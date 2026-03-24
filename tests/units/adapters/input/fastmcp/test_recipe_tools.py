from unittest.mock import AsyncMock, MagicMock

import fastmcp
import pytest
from fastmcp.exceptions import ToolError

from adapters.input.fastmcp.recipe_tools import RecipeMCP
from domain.models.recipe import RecipeResult


def _make_mcp() -> fastmcp.FastMCP:
    return fastmcp.FastMCP(name="test")


async def test_recipe_mcp_registers_tool():
    mcp = _make_mcp()
    RecipeMCP(MagicMock(), MagicMock(), mcp)
    tools = await mcp.list_tools()
    assert any(t.name == "ai_create_recipe" for t in tools)


async def test_ai_create_recipe_success():
    mcp = _make_mcp()
    service = MagicMock()
    service.ai_create = AsyncMock(return_value=RecipeResult(
        recipe_uuid="uuid-1",
        recipe_name="Carbonara",
        resolved_ingredients={},
        resolved_ustensils={},
        formatted_response="ok",
    ))
    RecipeMCP(service, MagicMock(), mcp)

    result = await mcp.call_tool("ai_create_recipe", {"raw_text": "pasta carbonara"})
    assert result.structured_content["recipe_uuid"] == "uuid-1"
    assert result.structured_content["recipe_name"] == "Carbonara"


async def test_ai_create_recipe_raises_on_error():
    mcp = _make_mcp()
    service = MagicMock()
    service.ai_create = AsyncMock(side_effect=RuntimeError("LLM down"))
    RecipeMCP(service, MagicMock(), mcp)

    with pytest.raises(ToolError, match="LLM down"):
        await mcp.call_tool("ai_create_recipe", {"raw_text": "some recipe"})
