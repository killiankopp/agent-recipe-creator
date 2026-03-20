from pathlib import Path

from arclith import Arclith

from adapters.input.fastmcp.tools import register_tools
from infrastructure.logging_setup import setup_logging

_logger = setup_logging()

arclith = Arclith(Path(__file__).parent / "config.yaml")
_logger.info("🚀 MCP stdio server starting")
mcp = arclith.fastmcp("Rekipe - Recipe Creator Agent")
register_tools(mcp, arclith)

if __name__ == "__main__":
    arclith.run_mcp_stdio(mcp)
