from pathlib import Path

import fastmcp
from adapters.input.fastmcp.recipe_tools import RecipeMCP
from arclith import Arclith
from infrastructure.config import load_agent_config
from infrastructure.container import build_container


def register_tools(mcp: fastmcp.FastMCP, arclith: Arclith) -> None:
    agent_config = load_agent_config(Path(__file__).parent.parent.parent.parent / "config.yaml")
    recipe_service, _, logger = build_container(arclith, agent_config)
    RecipeMCP(recipe_service, logger, mcp)
