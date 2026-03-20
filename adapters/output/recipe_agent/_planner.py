from adapters.output.recipe_agent._logger import log as logger
from domain.models.recipe import RecipePlan
from infrastructure.config import LMSettings
from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIModelProfile
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.openai import OpenAIProvider

_SYSTEM_PROMPT = (
    "Tu es un assistant d'extraction culinaire. "
    "À partir d'une description en langage naturel, tu structures une recette complète. "
    "Extrais le nombre de portions (servings) et les temps de préparation/cuisson si mentionnés. "
    "Identifie tous les ingrédients avec leur quantité et leur unité si mentionnées. "
    "Identifie tous les ustensiles nécessaires. "
    "Décompose la recette en étapes ordonnées : donne un titre court et une instruction complète à chaque étape, "
    "ainsi que la durée estimée en minutes si elle est précisée ou déductible. "
    "Dans chaque étape, utilise uniquement des ingrédients et ustensiles présents dans les listes. "
    "Déduis un nom de recette si non explicitement donné. "
    "Réponds toujours en français."
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
        self._agent: Agent = Agent(
            _build_model(settings),
            output_type = RecipePlan,
            system_prompt = _SYSTEM_PROMPT,
            retries = 3,
        )

    async def plan(self, user_input: str) -> RecipePlan:
        result = await self._agent.run(user_input)
        self._log_messages(result)
        usage = result.usage()
        logger.debug(
            f"  LLM usage requests={usage.requests} "
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
