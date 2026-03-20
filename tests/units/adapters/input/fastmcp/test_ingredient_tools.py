import json
from unittest.mock import AsyncMock, patch

import fastmcp
import pytest

from adapters.input.fastmcp.ingredient_tools import IngredientMCP
from application.services.ingredient_service import IngredientService


@pytest.fixture
def mcp_app():
    return fastmcp.FastMCP("test")


@pytest.fixture
def service(repo, logger):
    return IngredientService(repo, logger)


@pytest.fixture
async def client(service, logger, mcp_app):
    with patch("adapters.input.fastmcp.ingredient_tools.inject_tenant_uri", new = AsyncMock()):
        IngredientMCP(service, logger, mcp_app)
        async with fastmcp.Client(mcp_app) as c:
            yield c


def _data(result) -> dict | list | None:
    if not result.content:
        return result.data
    return json.loads(result.content[0].text)


@pytest.fixture
async def created_uuid(client) -> str:
    result = await client.call_tool("create_ingredient", {"name": "Farine", "unit": "kg"})
    data = _data(result)
    assert isinstance(data, dict)
    return data["uuid"]


# --- create_ingredient ---

async def test_create_returns_uuid(client):
    result = await client.call_tool("create_ingredient", {"name": "Farine"})
    assert "uuid" in _data(result)


async def test_create_with_unit(client):
    result = await client.call_tool("create_ingredient", {"name": "Sel", "unit": "g"})
    assert _data(result)["unit"] == "g"


# --- get_ingredient ---

async def test_get_found(client, created_uuid):
    result = await client.call_tool("get_ingredient", {"uuid": created_uuid})
    assert _data(result)["name"] == "Farine"


async def test_get_not_found_returns_none(client):
    result = await client.call_tool("get_ingredient", {"uuid": "01951234-5678-7abc-def0-000000000000"})
    assert _data(result) is None


# --- update_ingredient ---

async def test_update_changes_name(client, created_uuid):
    await client.call_tool("update_ingredient", {"uuid": created_uuid, "name": "Farine T55"})
    result = await client.call_tool("get_ingredient", {"uuid": created_uuid})
    assert _data(result)["name"] == "Farine T55"


# --- delete_ingredient ---

async def test_delete_hides_ingredient(client, created_uuid):
    await client.call_tool("delete_ingredient", {"uuid": created_uuid})
    result = await client.call_tool("get_ingredient", {"uuid": created_uuid})
    assert _data(result) is None


# --- list_ingredients ---

async def test_list_all(client):
    await client.call_tool("create_ingredient", {"name": "Farine"})
    await client.call_tool("create_ingredient", {"name": "Sel"})
    result = await client.call_tool("list_ingredients", {})
    assert len(_data(result)) == 2


async def test_list_filtered(client):
    await client.call_tool("create_ingredient", {"name": "Farine de blé"})
    await client.call_tool("create_ingredient", {"name": "Sel fin"})
    result = await client.call_tool("list_ingredients", {"name": "farine"})
    items = _data(result)
    assert len(items) == 1
    assert items[0]["name"] == "Farine de blé"


# --- duplicate_ingredient ---

async def test_duplicate_returns_new_uuid(client, created_uuid):
    result = await client.call_tool("duplicate_ingredient", {"uuid": created_uuid})
    assert _data(result)["uuid"] != created_uuid


# --- purge_ingredients ---

async def test_purge_returns_count(client):
    result = await client.call_tool("purge_ingredients", {})
    assert "purged" in _data(result)
