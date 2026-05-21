from application.use_cases.process_raw_recipe import ProcessRawRecipeUseCase
from domain.models.recipe import RecipeResult


class RecipeService:
    def __init__(self, use_case: ProcessRawRecipeUseCase) -> None:
        self._use_case = use_case

    async def ai_create(self, raw_text: str, *, allow_duplicate: bool = False) -> RecipeResult:
        return await self._use_case.execute(raw_text, allow_duplicate = allow_duplicate)
