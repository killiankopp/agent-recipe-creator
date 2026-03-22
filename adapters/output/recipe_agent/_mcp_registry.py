import json
from typing import Any

import time
from langchain_mcp_adapters.client import MultiServerMCPClient

from adapters.output.recipe_agent._logger import log as logger


class _MCPRecipeRegistry:
    def __init__(self, url: str) -> None:
        self._client = MultiServerMCPClient(
            {"rekipe": {"url": url, "transport": "streamable_http"}}
        )

    async def _call(self, tool_name: str, args: dict) -> Any:
        tools = await self._client.get_tools()
        tool = next((t for t in tools if t.name == tool_name), None)
        if tool is None:
            available = [t.name for t in tools]
            raise ValueError(f"MCP tool '{tool_name}' not found. Available: {available}")

        logger.debug(f"  → MCP {tool_name}({json.dumps(args, ensure_ascii = False)})")
        t0 = time.perf_counter()
        result = await tool.ainvoke(args)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        if result is None:
            logger.debug(f"  ← MCP {tool_name} None ({elapsed_ms:.0f}ms)")
            return None
        if not result:
            logger.debug(f"  ← MCP {tool_name} [] ({elapsed_ms:.0f}ms)")
            return []
        if isinstance(result, list) and isinstance(result[0], dict) and result[0].get("type") == "text":
            parsed = json.loads(result[0]["text"])
            logger.debug(f"  ← MCP {tool_name} {json.dumps(parsed, ensure_ascii = False)[:200]} ({elapsed_ms:.0f}ms)")
            return parsed

        logger.debug(f"  ← MCP {tool_name} {repr(result)[:200]} ({elapsed_ms:.0f}ms)")
        return result

    # ── Ingredients ───────────────────────────────────────────────────────────

    async def list_ingredients(self, name: str) -> list[dict]:
        return await self._call("list_ingredients", {"name": name})

    async def create_ingredient(self, name: str, unit: str | None) -> dict:
        return await self._call("create_ingredient", {"name": name, "unit": unit})

    async def get_ingredient(self, uuid: str) -> dict | None:
        return await self._call("get_ingredient", {"uuid": uuid})

    async def update_ingredient(self, uuid: str, name: str, unit: str | None) -> dict:
        return await self._call("update_ingredient", {"uuid": uuid, "name": name, "unit": unit})

    async def delete_ingredient(self, uuid: str) -> None:
        await self._call("delete_ingredient", {"uuid": uuid})

    async def duplicate_ingredient(self, uuid: str) -> dict:
        return await self._call("duplicate_ingredient", {"uuid": uuid})

    async def purge_ingredients(self) -> dict:
        return await self._call("purge_ingredients", {})

    # ── Ustensils ─────────────────────────────────────────────────────────────

    async def list_ustensils(self, name: str) -> list[dict]:
        return await self._call("list_ustensils", {"name": name})

    async def create_ustensil(self, name: str) -> dict:
        return await self._call("create_ustensil", {"name": name})

    async def get_ustensil(self, uuid: str) -> dict | None:
        return await self._call("get_ustensil", {"uuid": uuid})

    async def update_ustensil(self, uuid: str, name: str) -> dict:
        return await self._call("update_ustensil", {"uuid": uuid, "name": name})

    async def delete_ustensil(self, uuid: str) -> None:
        await self._call("delete_ustensil", {"uuid": uuid})

    async def duplicate_ustensil(self, uuid: str) -> dict:
        return await self._call("duplicate_ustensil", {"uuid": uuid})

    async def purge_ustensils(self) -> dict:
        return await self._call("purge_ustensils", {})

    # ── Recipes ───────────────────────────────────────────────────────────────

    async def list_recipes(self, name: str) -> list[dict]:
        return await self._call("list_recipes", {"name": name})

    async def create_recipe(self, name: str, description: str | None) -> dict:
        return await self._call("create_recipe", {"name": name, "description": description})

    async def get_recipe(self, uuid: str) -> dict | None:
        return await self._call("get_recipe", {"uuid": uuid})

    async def update_recipe(
            self, uuid: str, name: str, description: str | None, nutriscore: str | None = None
    ) -> dict:
        return await self._call(
            "update_recipe", {"uuid": uuid, "name": name, "description": description, "nutriscore": nutriscore}
        )

    async def delete_recipe(self, uuid: str) -> None:
        await self._call("delete_recipe", {"uuid": uuid})

    async def duplicate_recipe(self, uuid: str) -> dict:
        return await self._call("duplicate_recipe", {"uuid": uuid})

    async def purge_recipes(self) -> dict:
        return await self._call("purge_recipes", {})

    # ── Recipe ↔ Ingredient ───────────────────────────────────────────────────

    async def link_ingredient_to_recipe(self, recipe_uuid: str, ingredient_uuid: str) -> dict:
        return await self._call(
            "link_ingredient_to_recipe", {"recipe_uuid": recipe_uuid, "ingredient_uuid": ingredient_uuid}
        )

    async def unlink_ingredient_from_recipe(self, recipe_uuid: str, ingredient_uuid: str) -> None:
        await self._call(
            "unlink_ingredient_from_recipe", {"recipe_uuid": recipe_uuid, "ingredient_uuid": ingredient_uuid}
        )

    async def list_recipe_ingredients(self, recipe_uuid: str) -> list[dict]:
        return await self._call("list_recipe_ingredients", {"recipe_uuid": recipe_uuid})

    # ── Recipe ↔ Ustensil ─────────────────────────────────────────────────────

    async def link_ustensil_to_recipe(self, recipe_uuid: str, ustensil_uuid: str) -> dict:
        return await self._call(
            "link_ustensil_to_recipe", {"recipe_uuid": recipe_uuid, "ustensil_uuid": ustensil_uuid}
        )

    async def unlink_ustensil_from_recipe(self, recipe_uuid: str, ustensil_uuid: str) -> None:
        await self._call(
            "unlink_ustensil_from_recipe", {"recipe_uuid": recipe_uuid, "ustensil_uuid": ustensil_uuid}
        )

    async def list_recipe_ustensils(self, recipe_uuid: str) -> list[dict]:
        return await self._call("list_recipe_ustensils", {"recipe_uuid": recipe_uuid})

    # ── Steps ─────────────────────────────────────────────────────────────────

    async def create_step(self, recipe_uuid: str, name: str, description: str | None) -> dict:
        return await self._call("create_step", {"recipe_uuid": recipe_uuid, "name": name, "description": description})

    async def get_step(self, uuid: str) -> dict | None:
        return await self._call("get_step", {"uuid": uuid})

    async def update_step(self, uuid: str, name: str, description: str | None) -> dict | None:
        return await self._call("update_step", {"uuid": uuid, "name": name, "description": description})

    async def delete_step(self, uuid: str) -> None:
        await self._call("delete_step", {"uuid": uuid})

    async def list_steps(self, name: str | None = None) -> list[dict]:
        return await self._call("list_steps", {"name": name})

    async def list_steps_for_recipe(self, recipe_uuid: str) -> list[dict]:
        return await self._call("list_steps_for_recipe", {"recipe_uuid": recipe_uuid})

    async def duplicate_step(self, uuid: str) -> dict:
        return await self._call("duplicate_step", {"uuid": uuid})

    async def purge_steps(self) -> dict:
        return await self._call("purge_steps", {})
