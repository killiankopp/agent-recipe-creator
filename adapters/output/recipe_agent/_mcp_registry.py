import json
from typing import Any

import time
from adapters.output.recipe_agent._logger import log as logger
from langchain_mcp_adapters.client import MultiServerMCPClient


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

        if not result:
            logger.debug(f"  ← MCP {tool_name} [] ({elapsed_ms:.0f}ms)")
            return []
        if isinstance(result, list) and isinstance(result[0], dict) and result[0].get("type") == "text":
            parsed = json.loads(result[0]["text"])
            logger.debug(f"  ← MCP {tool_name} {json.dumps(parsed, ensure_ascii = False)[:200]} ({elapsed_ms:.0f}ms)")
            return parsed

        logger.debug(f"  ← MCP {tool_name} {repr(result)[:200]} ({elapsed_ms:.0f}ms)")
        return result

    async def list_ingredients(self, name: str) -> list[dict]:
        return await self._call("list_ingredients", {"name": name})

    async def create_ingredient(self, name: str, unit: str | None) -> dict:
        return await self._call("create_ingredient", {"name": name, "unit": unit})

    async def list_ustensils(self, name: str) -> list[dict]:
        return await self._call("list_ustensils", {"name": name})

    async def create_ustensil(self, name: str) -> dict:
        return await self._call("create_ustensil", {"name": name})

    async def create_recipe(self, name: str, description: str | None) -> dict:
        return await self._call("create_recipe", {"name": name, "description": description})
