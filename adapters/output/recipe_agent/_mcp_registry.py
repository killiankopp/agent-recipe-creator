import json
import time
from typing import Any

import httpx

from adapters.output.recipe_agent._logger import log as logger


class _MCPRecipeRegistry:
    def __init__(self, url: str, api_url: str, tenant_uri: str) -> None:
        self._mcp_url = url
        self._api_url = api_url.rstrip("/")
        self._tenant_uri = tenant_uri

    async def _call(self, tool_name: str, args: dict) -> Any:
        logger.debug(f"  → MCP {tool_name}({json.dumps(args, ensure_ascii = False)})")
        t0 = time.perf_counter()
        result = await self._call_http(tool_name, args)
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

    async def _call_http(self, tool_name: str, args: dict) -> Any:
        headers = {"X-Tenant-URI": self._tenant_uri}
        async with httpx.AsyncClient(base_url=self._api_url, timeout=30.0, headers=headers) as client:
            match tool_name:
                case "list_ingredients":
                    return await self._get_page(client, "/v1/ingredients/", {"name": args["name"]})
                case "create_ingredient":
                    return await self._post_representation(
                        client,
                        "/v1/ingredients/",
                        {"name": args["name"], "unit": args.get("unit")},
                    )
                case "list_equipment":
                    return await self._get_page(client, "/v1/equipment/", {"name": args["name"]})
                case "create_equipment":
                    return await self._post_representation(client, "/v1/equipment/", {"name": args["name"]})
                case "list_recipes":
                    return await self._get_page(client, "/v1/recipes/", {"name": args["name"]})
                case "create_recipe":
                    return await self._post_representation(client, "/v1/recipes/", args["payload"])
                case _:
                    raise ValueError(
                        f"Recipe registry operation '{tool_name}' is not supported by the HTTP adapter "
                        f"(MCP URL configured: {self._mcp_url})"
                    )

    @staticmethod
    async def _get_page(client: httpx.AsyncClient, path: str, params: dict[str, Any]) -> list[dict]:
        response = await client.get(path, params={**params, "page": 1, "per_page": 50})
        response.raise_for_status()
        payload = response.json()
        return payload.get("data") or []

    @staticmethod
    async def _post_representation(client: httpx.AsyncClient, path: str, payload: dict[str, Any]) -> dict:
        response = await client.post(path, json=payload, headers={"Prefer": "return=representation"})
        response.raise_for_status()
        data = response.json().get("data")
        if not isinstance(data, dict):
            raise ValueError(f"Invalid response from {path}: expected object data")
        return data

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

    # ── Equipment ─────────────────────────────────────────────────────────────

    async def list_equipment(self, name: str) -> list[dict]:
        return await self._call("list_equipment", {"name": name})

    async def create_equipment(self, name: str) -> dict:
        return await self._call("create_equipment", {"name": name})

    async def list_ustensils(self, name: str) -> list[dict]:
        return await self.list_equipment(name)

    async def create_ustensil(self, name: str) -> dict:
        return await self.create_equipment(name)

    # ── Recipes ───────────────────────────────────────────────────────────────

    async def list_recipes(self, name: str) -> list[dict]:
        return await self._call("list_recipes", {"name": name})

    async def create_recipe(self, payload: dict) -> dict:
        return await self._call("create_recipe", {"payload": payload})

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
