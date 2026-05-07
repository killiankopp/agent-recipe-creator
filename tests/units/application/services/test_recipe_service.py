from application.services.recipe_service import RecipeService
from application.use_cases.process_raw_recipe import ProcessRawRecipeUseCase
from arclith import InMemoryRepository
from domain.models.agent_run import AgentRun
from domain.models.recipe import RecipeResult
from domain.ports.recipe_agent import RecipeAgentPort
from tests.units.conftest import NullLogger


class _StubAgent(RecipeAgentPort):
    def __init__(self, result: RecipeResult) -> None:
        self._result = result

    async def process(
            self,
            raw_text: str,
            run_uuid: str,
            *,
            allow_duplicate: bool = False,
    ) -> RecipeResult:
        return self._result


async def test_ai_create_returns_result():
    expected = RecipeResult(
        recipe_uuid = "r-1",
        recipe_name = "Crêpes",
        resolved_ingredients = {"farine": "i-1"},
        resolved_ustensils = {},
        formatted_response = "✅ Crêpes",
    )
    use_case = ProcessRawRecipeUseCase(
        _StubAgent(expected), InMemoryRepository[AgentRun](), NullLogger()
    )
    service = RecipeService(use_case)
    result = await service.ai_create("recette de crêpes")
    assert result.recipe_uuid == "r-1"
    assert result.recipe_name == "Crêpes"


async def test_ai_create_passes_raw_text_to_agent():
    received: list[tuple[str, bool]] = []

    class _CapturingAgent(RecipeAgentPort):
        async def process(
                self,
                raw_text: str,
                run_uuid: str,
                *,
                allow_duplicate: bool = False,
        ) -> RecipeResult:
            received.append((raw_text, allow_duplicate))
            return RecipeResult(
                recipe_uuid = "r-2",
                recipe_name = "Test",
                resolved_ingredients = {},
                resolved_ustensils = {},
                formatted_response = "✅",
            )

    use_case = ProcessRawRecipeUseCase(
        _CapturingAgent(), InMemoryRepository[AgentRun](), NullLogger()
    )
    service = RecipeService(use_case)
    await service.ai_create("ma recette personnalisée", allow_duplicate = True)
    assert received == [("ma recette personnalisée", True)]
