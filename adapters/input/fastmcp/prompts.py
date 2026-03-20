import fastmcp

from adapters.input.fastmcp.dependencies import inject_tenant_uri
from application.services.ingredient_service import IngredientService
from arclith.domain.ports.logger import Logger


class IngredientPrompts:
    def __init__(self, service: IngredientService, logger: Logger, mcp: fastmcp.FastMCP) -> None:
        self._service = service
        self._logger = logger
        self._mcp = mcp
        self._register_prompts()

    def _register_prompts(self) -> None:
        service = self._service

        @self._mcp.prompt
        async def suggest_recipe(ctx: fastmcp.Context) -> list[dict]:
            """Suggest a recipe based on all available ingredients."""
            await inject_tenant_uri(ctx)
            items = await service.find_all()
            names = ", ".join(i.name for i in items) or "no ingredients available"
            return [{"role": "user", "content": f"Available ingredients: {names}. Suggest a simple recipe using these ingredients."}]

        @self._mcp.prompt
        def how_to_use(ingredient_name: str) -> list[dict]:
            """Explain how and in what dishes to use a given ingredient."""
            return [{"role": "user", "content": f"Explain how to use '{ingredient_name}' in cooking: pairings, cooking methods, and typical dishes."}]

