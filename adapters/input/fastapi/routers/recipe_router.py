from fastapi import APIRouter, HTTPException

from adapters.input.schemas.recipe_schema import AiCreateRequestSchema, AiCreateResponseSchema
from application.services.recipe_service import RecipeService
from arclith.adapters.input.schemas import ApiResponse, success_response
from arclith.domain.ports.logger import Logger


class RecipeRouter:
    def __init__(self, service: RecipeService, logger: Logger) -> None:
        self._service = service
        self._logger = logger
        self.router = APIRouter(prefix = "/v1/recipes", tags = ["recipes"])
        self._register_routes()

    def _register_routes(self) -> None:
        self.router.add_api_route(
            methods = ["POST"],
            path = "/ai-create",
            endpoint = self.ai_create,
            summary = "AI-create recipe",
            response_model = ApiResponse[AiCreateResponseSchema],
            response_description = "Recipe creation result with UUID and formatted output",
            status_code = 201,
        )

    async def ai_create(self, payload: AiCreateRequestSchema) -> ApiResponse[AiCreateResponseSchema]:
        """Structure and register a raw recipe via AI agent."""
        try:
            result = await self._service.ai_create(payload.raw_text)
        except Exception as exc:
            self._logger.error("💥 ai_create failed via HTTP", error = str(exc))
            raise HTTPException(status_code = 500, detail = str(exc)) from exc
        return success_response(
            data = AiCreateResponseSchema(
                recipe_uuid = result.recipe_uuid,
                recipe_name = result.recipe_name,
                formatted_response = result.formatted_response,
            ),
            links = {"recipe": f"/v1/recipes/{result.recipe_uuid}"},
        )
