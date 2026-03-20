from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict


class LMSettings(BaseModel):
    model_config = ConfigDict(extra = "ignore")

    model_name: str
    provider: str = "openai"  # "openai" | "anthropic"
    base_url: str | None = None
    api_key: str = "local"


class LMConfig(BaseModel):
    model_config = ConfigDict(extra = "ignore")

    planner: LMSettings


class MCPRegistrySettings(BaseModel):
    model_config = ConfigDict(extra = "ignore")

    url: str


class FuzzySettings(BaseModel):
    model_config = ConfigDict(extra = "ignore")

    threshold: int = 80


class AgentConfig(BaseModel):
    model_config = ConfigDict(extra = "ignore")

    mcp_registry: MCPRegistrySettings
    lm: LMConfig
    fuzzy: FuzzySettings = FuzzySettings()


def load_agent_config(config_path: Path) -> AgentConfig:
    with config_path.open() as f:
        data = yaml.safe_load(f)
    return AgentConfig.model_validate(data or {})
