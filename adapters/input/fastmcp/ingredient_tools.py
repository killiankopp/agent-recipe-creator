from typing import Annotated
from uuid import UUID as StdUUID

import fastmcp
from pydantic import Field
from uuid6 import UUID

from adapters.input.fastmcp.dependencies import inject_tenant_uri
from adapters.input.schemas.ingredient_schema import IngredientSchema
from application.services.ingredient_service import IngredientService
from arclith.domain.ports.logger import Logger
from domain.models.ingredient import Ingredient


class IngredientMCP:
    def __init__(self, service: IngredientService, logger: Logger, mcp: fastmcp.FastMCP) -> None:
        self._service = service
        self._logger = logger
        self._mcp = mcp
        self._register_tools()

    @staticmethod
    def _to_uuid6(uuid: StdUUID) -> UUID:
        return UUID(str(uuid))

    def _register_tools(self) -> None:
        service = self._service
        logger = self._logger
        to_uuid6 = self._to_uuid6

        @self._mcp.tool
        async def create_ingredient(
            name: Annotated[str, Field(description="Nom de l'ingrédient.", examples=["Farine de blé"])],
            unit: Annotated[str | None, Field(default=None, description="Unité de mesure (ex. g, kg, ml). None si non applicable.", examples=["g", "kg", None])] = None,
                ctx: fastmcp.Context | None = None,
        ) -> dict:
            """Create a new ingredient."""
            await inject_tenant_uri(ctx)
            result = await service.create(Ingredient(name=name, unit=unit))
            logger.info("✅ Ingredient created via MCP", uuid = str(result.uuid), name = result.name)
            return IngredientSchema.model_validate(result).model_dump()

        @self._mcp.tool
        async def get_ingredient(
            uuid: Annotated[str, Field(description="UUID de l'ingrédient.", examples=["01951234-5678-7abc-def0-123456789abc"])],
                ctx: fastmcp.Context | None = None,
        ) -> dict | None:
            """Get an ingredient by its UUID."""
            await inject_tenant_uri(ctx)
            result = await service.read(to_uuid6(StdUUID(uuid)))
            if result is None:
                logger.warning("⚠️ Ingredient not found via MCP", uuid=uuid)
                return None
            logger.info("✅ Ingredient fetched via MCP", uuid = uuid, name = result.name)
            return IngredientSchema.model_validate(result).model_dump()

        @self._mcp.tool
        async def update_ingredient(
            uuid: Annotated[str, Field(description="UUID de l'ingrédient à modifier.", examples=["01951234-5678-7abc-def0-123456789abc"])],
            name: Annotated[str, Field(description="Nouveau nom de l'ingrédient.", examples=["Farine complète"])],
            unit: Annotated[str | None, Field(default=None, description="Nouvelle unité de mesure.", examples=["g", None])] = None,
                ctx: fastmcp.Context | None = None,
        ) -> dict:
            """Update an existing ingredient."""
            await inject_tenant_uri(ctx)
            result = await service.update(Ingredient(uuid=to_uuid6(StdUUID(uuid)), name=name, unit=unit))
            logger.info("✅ Ingredient updated via MCP", uuid = uuid, name = result.name)
            return IngredientSchema.model_validate(result).model_dump()

        @self._mcp.tool
        async def delete_ingredient(
            uuid: Annotated[str, Field(description="UUID de l'ingrédient à supprimer.", examples=["01951234-5678-7abc-def0-123456789abc"])],
                ctx: fastmcp.Context | None = None,
        ) -> None:
            """Delete an ingredient by its UUID."""
            await inject_tenant_uri(ctx)
            await service.delete(to_uuid6(StdUUID(uuid)))
            logger.info("✅ Ingredient deleted via MCP", uuid = uuid)

        @self._mcp.tool
        async def list_ingredients(
            name: Annotated[str | None, Field(default=None, description="Filtre par nom (recherche partielle, insensible à la casse).", examples=["farine", None])] = None,
                ctx: fastmcp.Context | None = None,
        ) -> list[dict]:
            """List all ingredients, optionally filtered by name."""
            await inject_tenant_uri(ctx)
            items = await service.find_by_name(name) if name else await service.find_all()
            logger.info("✅ Ingredients listed via MCP", count = len(items), filter = name)
            return [IngredientSchema.model_validate(i).model_dump() for i in items]

        @self._mcp.tool
        async def duplicate_ingredient(
            uuid: Annotated[str, Field(description="UUID de l'ingrédient à dupliquer.", examples=["01951234-5678-7abc-def0-123456789abc"])],
                ctx: fastmcp.Context | None = None,
        ) -> dict:
            """Duplicate an ingredient, assigning it a new UUID."""
            await inject_tenant_uri(ctx)
            result = await service.duplicate(to_uuid6(StdUUID(uuid)))
            logger.info("✅ Ingredient duplicated via MCP", source_uuid = uuid, new_uuid = str(result.uuid))
            return IngredientSchema.model_validate(result).model_dump()

        @self._mcp.tool
        async def purge_ingredients(ctx: fastmcp.Context | None = None) -> dict:
            """Purge all soft-deleted ingredients that have exceeded the retention period."""
            await inject_tenant_uri(ctx)
            purged = await service.purge()
            logger.info("✅ Ingredients purged via MCP", count = purged)
            return {"purged": purged}

