from pathlib import Path

from adapters.input.fastmcp.prompts import IngredientPrompts
from adapters.input.fastmcp.resources import IngredientResources
from adapters.input.fastmcp.tools import IngredientMCP
from arclith import Arclith
from infrastructure.container import build_ingredient_service
from infrastructure.logging_setup import setup_logging

_logger = setup_logging()

arclith = Arclith(Path(__file__).parent / "config.yaml")
service, logger = build_ingredient_service(arclith)
mcp = arclith.fastmcp("Rekipe - Ingredients")
_logger.info("🚀 MCP HTTP server starting", host = arclith.config.mcp.host, port = arclith.config.mcp.port)
IngredientMCP(service, logger, mcp)
IngredientResources(service, logger, mcp)
IngredientPrompts(service, logger, mcp)

if __name__ == "__main__":
    arclith.run_mcp_http(mcp)
