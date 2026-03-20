import fastmcp

from arclith import Arclith
from adapters.input.fastmcp.ingredient_tools import IngredientMCP
from infrastructure.ingredient_container import build_ingredient_service


def register_tools(mcp: fastmcp.FastMCP, arclith: Arclith) -> None:
    service, logger = build_ingredient_service(arclith)
    IngredientMCP(service, logger, mcp)
