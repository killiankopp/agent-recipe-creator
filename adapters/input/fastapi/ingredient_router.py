from uuid import UUID as StdUUID

from fastapi import APIRouter, Depends, HTTPException, Query
from uuid6 import UUID

from adapters.input.fastapi.dependencies import inject_tenant_uri
from adapters.input.schemas.ingredient_schema import (
    IngredientCreateSchema,
    IngredientPatchSchema,
    IngredientSchema,
    IngredientUpdateSchema,
    IngredientCreatedSchema,
)
from application.services.ingredient_service import IngredientService
from arclith.domain.ports.logger import Logger
from domain.models.ingredient import Ingredient


class IngredientRouter:
    def __init__(self, service: IngredientService, logger: Logger) -> None:
        self._service = service
        self._logger = logger
        self.router = APIRouter(prefix="/v1/ingredients", tags=["ingredients"], dependencies=[Depends(inject_tenant_uri)])
        self._register_routes()

    def _register_routes(self) -> None:
        self.router.add_api_route("/", self.create_ingredient, methods = ["POST"], response_model = IngredientCreatedSchema,
                                  status_code = 201, response_model_include = {"uuid"})
        self.router.add_api_route("/", self.list_ingredients, methods=["GET"], response_model=list[IngredientSchema])
        self.router.add_api_route("/purge", self.purge_ingredients, methods=["DELETE"], status_code=200)
        self.router.add_api_route("/{uuid}", self.get_ingredient, methods=["GET"], response_model=IngredientSchema)
        self.router.add_api_route("/{uuid}", self.update_ingredient, methods = ["PUT"], response_model = None,
                                  status_code = 204)
        self.router.add_api_route("/{uuid}", self.patch_ingredient, methods = ["PATCH"], response_model = None,
                                  status_code = 204)
        self.router.add_api_route("/{uuid}", self.delete_ingredient, methods=["DELETE"], status_code=204)
        self.router.add_api_route("/{uuid}/duplicate", self.duplicate_ingredient, methods=["POST"], response_model=IngredientSchema, status_code=201)

    @staticmethod
    def _to_uuid6(uuid: StdUUID) -> UUID:
        return UUID(str(uuid))

    async def create_ingredient(self, payload: IngredientCreateSchema) -> IngredientSchema:
        """Create a new ingredient."""
        result = await self._service.create(Ingredient(name=payload.name, unit=payload.unit))
        return IngredientSchema.model_validate(result, from_attributes = True)

    async def get_ingredient(self, uuid: StdUUID) -> IngredientSchema:
        """Get an ingredient by its UUID."""
        result = await self._service.read(self._to_uuid6(uuid))
        if result is None:
            self._logger.warning("⚠️ Ingredient not found via HTTP", uuid=str(uuid))
            raise HTTPException(status_code=404, detail="Ingredient not found")
        return IngredientSchema.model_validate(result, from_attributes = True)

    async def update_ingredient(self, uuid: StdUUID, payload: IngredientUpdateSchema) -> None:
        """Update an existing ingredient."""
        await self._service.update(Ingredient(uuid = self._to_uuid6(uuid), name = payload.name, unit = payload.unit))

    async def patch_ingredient(self, uuid: StdUUID, payload: IngredientPatchSchema) -> None:
        """Partially update an ingredient."""
        existing = await self._service.read(self._to_uuid6(uuid))
        if existing is None:
            self._logger.warning("⚠️ Ingredient not found via HTTP", uuid=str(uuid))
            raise HTTPException(status_code=404, detail="Ingredient not found")
        await self._service.update(Ingredient(
            uuid=existing.uuid,
            name=payload.name if payload.name is not None else existing.name,
            unit=payload.unit if payload.unit is not None else existing.unit,
        ))


    async def delete_ingredient(self, uuid: StdUUID) -> None:
        """Delete an ingredient by its UUID."""
        await self._service.delete(self._to_uuid6(uuid))

    async def list_ingredients(
        self,
        name: str | None = Query(
            default=None,
            min_length=1,
            description="Filtre par nom (recherche partielle, insensible à la casse).",
            examples=["farine"],
        ),
    ) -> list[IngredientSchema]:
        """List all ingredients, optionally filtered by name."""
        items = await self._service.find_by_name(name) if name else await self._service.find_all()
        return [IngredientSchema.model_validate(i, from_attributes = True) for i in items]

    async def duplicate_ingredient(self, uuid: StdUUID) -> IngredientSchema:
        """Duplicate an ingredient, assigning it a new UUID."""
        result = await self._service.duplicate(self._to_uuid6(uuid))
        return IngredientSchema.model_validate(result, from_attributes = True)

    async def purge_ingredients(self) -> dict:
        """Purge all soft-deleted ingredients that have exceeded the retention period."""
        purged = await self._service.purge()
        return {"purged": purged}

