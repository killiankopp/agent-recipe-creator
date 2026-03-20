from typing import Annotated

import fastmcp
from adapters.input.schemas.recipe_schema import AiCreateResponseSchema
from application.services.recipe_service import RecipeService
from arclith.domain.ports.logger import Logger
from pydantic import Field


class RecipeMCP:
    def __init__(self, service: RecipeService, logger: Logger, mcp: fastmcp.FastMCP) -> None:
        self._service = service
        self._logger = logger
        self._mcp = mcp
        self._register_tools()

    def _register_tools(self) -> None:
        service = self._service
        logger = self._logger

        @self._mcp.tool
        async def ai_create_recipe(
                raw_text: Annotated[
                    str,
                    Field(
                        description = "Texte brut de la recette : copier/coller internet, OCR, saisie libre…",
                        examples = ["Tarte tatin : 6 pommes, 150g beurre, 200g sucre…"],
                    ),
                ],
        ) -> dict:
            """Structure and register a raw recipe via AI agent."""
            try:
                result = await service.ai_create(raw_text)
            except Exception as exc:
                logger.error("💥 ai_create_recipe failed via MCP", error = str(exc))
                raise
            logger.info("✅ Recipe created via MCP", recipe_uuid = result.recipe_uuid, name = result.recipe_name)
            return AiCreateResponseSchema(
                recipe_uuid = result.recipe_uuid,
                recipe_name = result.recipe_name,
                formatted_response = result.formatted_response,
            ).model_dump()
