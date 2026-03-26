import pytest
from fastapi import HTTPException

from adapters.input.fastapi.routers.recipe_router import RecipeRouter
from adapters.input.schemas.recipe_schema import AiCreateRequestSchema
from application.services.recipe_service import RecipeService
from application.use_cases.process_raw_recipe import ProcessRawRecipeUseCase
from arclith import InMemoryRepository
from domain.models.agent_run import AgentRun
from domain.models.recipe import RecipeResult
from domain.ports.output.recipe_agent import RecipeAgentPort
from tests.units.conftest import NullLogger


class _SuccessAgent(RecipeAgentPort):
    async def process(self, raw_text: str, run_uuid: str) -> RecipeResult:
        return RecipeResult(
            recipe_uuid = "r-uuid",
            recipe_name = "Tarte au citron",
            resolved_ingredients = {"citron": "i-1"},
            resolved_ustensils = {"moule": "u-1"},
            formatted_response = "✅ Tarte au citron créée",
        )


class _FailingAgent(RecipeAgentPort):
    async def process(self, raw_text: str, run_uuid: str) -> RecipeResult:
        raise RuntimeError("agent failed")


def _make_router(agent: RecipeAgentPort) -> RecipeRouter:
    use_case = ProcessRawRecipeUseCase(agent, InMemoryRepository[AgentRun](), NullLogger())
    service = RecipeService(use_case)
    return RecipeRouter(service, NullLogger())


async def test_ai_create_success():
    router = _make_router(_SuccessAgent())
    payload = AiCreateRequestSchema(raw_text = "Une recette de tarte classique au citron meringuée")
    result = await router.ai_create(payload)
    assert result.status == "success"
    assert result.data.recipe_uuid == "r-uuid"
    assert result.data.recipe_name == "Tarte au citron"
    assert "Tarte" in result.data.formatted_response


async def test_ai_create_raises_500_on_agent_failure():
    router = _make_router(_FailingAgent())
    payload = AiCreateRequestSchema(raw_text = "Recette qui va échouer lors du traitement agent")
    with pytest.raises(HTTPException) as exc_info:
        await router.ai_create(payload)
    assert exc_info.value.status_code == 500
    assert "agent failed" in exc_info.value.detail
