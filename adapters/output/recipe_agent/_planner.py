from typing import cast

from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIModelProfile
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.openai import OpenAIProvider

from adapters.output.recipe_agent._logger import log as logger
from domain.models.recipe import RecipePlan
from infrastructure.config import LMSettings

_SYSTEM_PROMPT = (
    "Tu es un assistant d'extraction culinaire. "
    "À partir d'une description en langage naturel, tu structures une recette complète. "
    "\n\n"
    "## Nom de la recette\n"
    "Détermine un nom court, canonique et normalisé (ex. 'Tarte Tatin', 'Pizza Margherita', 'Soupe à l'oignon'). "
    "Ne préfixe jamais avec 'Recette de' ou 'La recette'. "
    "Ce nom sera utilisé pour rechercher si la recette existe déjà — sois précis et cohérent.\n\n"
    "## Ingrédients\n"
    "Identifie tous les ingrédients avec leur quantité et leur unité si mentionnées. "
    "Si la quantité ou l'unité est implicite, propose une valeur utilisable (ex. '1' + 'pincée', "
    "'1' + 'pièce', '1' + 'unité') plutôt que de laisser vide. "
    "Normalise les noms (ex. 'farine de blé', 'sel fin') sans majuscule inutile.\n\n"
    "## Ustensiles\n"
    "Identifie tous les ustensiles nécessaires à la réalisation. "
    "Normalise les noms (ex. 'fouet', 'casserole 20 cm').\n\n"
    "## Étapes\n"
    "Décompose la recette en étapes ordonnées : donne un titre court et une instruction complète à chaque étape, "
    "ainsi que la durée estimée en minutes si elle est précisée ou déductible. "
    "Dans chaque étape, utilise uniquement des ingrédients et ustensiles présents dans les listes.\n\n"
    "## Recettes composées\n"
    "Quand la recette est structurée en préparations distinctes (ex. meringue, caramel, crème anglaise), "
    "renseigne chaque préparation dans `components` avec ses propres ingrédients, ustensiles et étapes. "
    "La recette principale doit alors contenir seulement les étapes d'assemblage globales si elles existent.\n\n"
    "## Métadonnées\n"
    "Extrais le nombre de portions (servings) et les temps de préparation/cuisson si mentionnés.\n\n"
    "Réponds toujours en français."
)

_REVIEW_PROMPT = (
    "Tu es un relecteur culinaire qualité. "
    "Tu reçois le texte brut et un JSON de recette déjà extrait. "
    "Retourne une version corrigée du même schéma RecipePlan.\n\n"
    "Objectif principal : cohérence ingrédients ↔ étapes.\n"
    "- Chaque ingrédient explicitement utilisé dans une étape doit exister dans la liste d'ingrédients de la recette ou de sa sous-recette.\n"
    "- Chaque étape doit utiliser les noms canoniques présents dans la liste d'ingrédients.\n"
    "- Si un ingrédient manque mais que sa quantité est inconnue, ajoute-le avec quantity='1' et unit='unité'.\n"
    "- Ne supprime pas une sous-recette utile.\n"
    "- Garde une réponse en français et ne renvoie que le JSON structuré."
)

# 'prompted' avoids tool-calling (unreliable on local LLMs like Qwen3/LLaMA).
# openai_chat_send_back_thinking_parts=False prevents thinking tokens from
# accumulating in retry context and blowing the context window.
_LOCAL_PROFILE = OpenAIModelProfile(
    default_structured_output_mode = "prompted",
    openai_chat_send_back_thinking_parts = False,
)


def _build_model(settings: LMSettings):
    if settings.provider == "anthropic":
        logger.debug(f"planner provider=anthropic model={settings.model_name}")
        return AnthropicModel(
            settings.model_name,
            provider = AnthropicProvider(api_key = settings.api_key),
        )
    if not settings.base_url:
        raise ValueError("base_url is required for provider='openai'")
    logger.debug(f"planner provider=openai model={settings.model_name} base_url={settings.base_url}")
    return OpenAIChatModel(
        settings.model_name,
        provider = OpenAIProvider(base_url = settings.base_url, api_key = settings.api_key),
        profile = _LOCAL_PROFILE,
    )


class _PydanticAIPlanner:
    def __init__(self, settings: LMSettings) -> None:
        self._agent = cast(Agent[None, RecipePlan], Agent(
            _build_model(settings),
            output_type=RecipePlan,
            system_prompt=_SYSTEM_PROMPT,
            retries=3,
        ))
        self._review_agent = cast(Agent[None, RecipePlan], Agent(
            _build_model(settings),
            output_type=RecipePlan,
            system_prompt=_REVIEW_PROMPT,
            retries=3,
        ))

    async def plan(self, user_input: str) -> RecipePlan:
        result = await self._agent.run(user_input)
        self._log_messages(result)
        usage = result.usage()
        logger.debug(
            f"  LLM usage requests={usage.requests} "
            f"input={usage.input_tokens} output={usage.output_tokens} total={usage.total_tokens}"
        )
        return result.output

    async def review(self, raw_text: str, plan: RecipePlan) -> RecipePlan:
        review_input = (
            "TEXTE BRUT:\n"
            f"{raw_text}\n\n"
            "RECETTE EXTRAITE JSON:\n"
            f"{plan.model_dump_json()}"
        )
        result = await self._review_agent.run(review_input)
        self._log_messages(result)
        usage = result.usage()
        logger.debug(
            f"  review LLM usage requests={usage.requests} "
            f"input={usage.input_tokens} output={usage.output_tokens} total={usage.total_tokens}"
        )
        return result.output

    @staticmethod
    def _log_messages(result) -> None:
        for msg in result.all_messages():
            for part in getattr(msg, "parts", []):
                kind = type(part).__name__
                match kind:
                    case "ThinkingPart":
                        logger.debug(f"  LLM thinking ({len(part.content)} chars): {part.content[:300]!r}")
                    case "TextPart":
                        logger.debug(f"  LLM text: {part.content[:500]!r}")
                    case "ToolCallPart":
                        logger.debug(f"  LLM tool_call name={part.tool_name} args={str(part.args)[:300]}")
