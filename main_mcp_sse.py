from pathlib import Path

from adapters.input.fastmcp.tools import register_tools
from arclith import Arclith
from infrastructure.logging_setup import setup_logging

_logger = setup_logging()

arclith = Arclith(Path(__file__).parent / "config.yaml")
_logger.info("🚀 MCP SSE server starting", host = arclith.config.mcp.host, port = arclith.config.mcp.port)
mcp = arclith.fastmcp("Rekipe")
register_tools(mcp, arclith)

if __name__ == "__main__":
    arclith.run_mcp_sse(mcp)
