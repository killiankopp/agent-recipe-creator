from adapters.input.schemas.recipe_schema import AiCreateRequestSchema, AiCreateResponseSchema
from application.services.recipe_service import RecipeService
from arclith.domain.ports.logger import Logger
from fastapi import APIRouter, HTTPException, Response, status


class RecipeRouter:
    def __init__(self, service: RecipeService, logger: Logger) -> None:
        self._service = service
        self._logger = logger
        self.router = APIRouter(prefix = "/v1/recipes", tags = ["recipes"])
        self._register_routes()

    def _register_routes(self) -> None:
        self.router.add_api_route(
            "/ai-create",
            self.ai_create,
            methods = ["POST"],
            response_model = AiCreateResponseSchema,
            status_code = 201,
        )

    async def ai_create(
            self,
            payload: AiCreateRequestSchema,
            response: Response,
    ) -> AiCreateResponseSchema:
        """Structure and register a raw recipe via AI agent."""
        try:
            result = await self._service.ai_create(payload.raw_text, allow_duplicate = payload.allow_duplicate)
        except Exception as exc:
            self._logger.error("💥 ai_create failed via HTTP", error = str(exc))
            raise HTTPException(status_code = 500, detail = str(exc)) from exc
        if not result.created:
            response.status_code = status.HTTP_200_OK
        return AiCreateResponseSchema(
            recipe_uuid = result.recipe_uuid,
            recipe_name = result.recipe_name,
            formatted_response = result.formatted_response,
            created = result.created,
            duplicate_confirmation_required = result.duplicate_confirmation_required,
            existing_recipe_uuid = result.existing_recipe_uuid,
            existing_recipe_name = result.existing_recipe_name,
        )
