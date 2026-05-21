from pathlib import Path
from typing import Any

import os
from copy import deepcopy

from arclith.infrastructure.secret_factory import build_secret_resolver
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


class RecipeAPISettings(BaseModel):
    model_config = ConfigDict(extra = "ignore")

    url: str = "http://127.0.0.1:8301"
    tenant_uri: str = "foyer-demo"


class FuzzySettings(BaseModel):
    model_config = ConfigDict(extra = "ignore")

    threshold: int = 80


class AgentConfig(BaseModel):
    model_config = ConfigDict(extra = "ignore")

    mcp_registry: MCPRegistrySettings
    recipe_api: RecipeAPISettings = RecipeAPISettings()
    lm: LMConfig
    fuzzy: FuzzySettings = FuzzySettings()


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open() as f:
        data = yaml.safe_load(f)
    return data or {}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(current, value)
        else:
            merged[key] = value
    return merged


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, list):
        return [_expand_env(item) for item in value]
    if isinstance(value, dict):
        return {key: _expand_env(item) for key, item in value.items()}
    return value


def _load_secret_resolver_config(config_path: Path, secret_config_path: Path | None = None) -> dict[str, Any]:
    path = secret_config_path or config_path.parent / "config" / "secrets.yaml"
    data = _load_yaml(path)
    if not data:
        return {}
    return {"secrets": _normalize_secret_config(data, config_path.parent)}


def _normalize_secret_config(data: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    normalized = deepcopy(data)
    yaml_config = normalized.get("yaml")
    if not isinstance(yaml_config, dict):
        return normalized

    yaml_path = yaml_config.get("path")
    if not isinstance(yaml_path, str) or not yaml_path:
        return normalized

    path = Path(yaml_path)
    if not path.is_absolute():
        yaml_config["path"] = str((base_dir / path).resolve())
    return normalized


def _get_nested(data: dict[str, Any], path: str) -> Any:
    current: Any = data
    for key in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _set_nested(data: dict[str, Any], path: str, value: str) -> None:
    current: dict[str, Any] = data
    keys = path.split(".")
    for key in keys[:-1]:
        next_value = current.get(key)
        if not isinstance(next_value, dict):
            next_value = {}
            current[key] = next_value
        current = next_value
    current[keys[-1]] = value


def _is_resolved_secret(value: Any) -> bool:
    if value is None:
        return False
    if not isinstance(value, str):
        return True
    stripped = value.strip()
    return bool(stripped) and not stripped.startswith("${") and stripped != "sk-ant-XXXX"


def _resolve_config_secrets(data: dict[str, Any]) -> dict[str, Any]:
    resolver = build_secret_resolver(data)
    if resolver is None:
        return data

    result = deepcopy(data)
    mappings: dict[str, str] = (result.get("secrets") or {}).get("mappings") or {}
    missing: list[str] = []
    for field_path, secret_key in mappings.items():
        value = resolver.get(field_path, secret_key)
        if value is not None:
            _set_nested(result, field_path, value)
        elif not _is_resolved_secret(_get_nested(result, field_path)):
            missing.append(field_path)

    if missing:
        raise RuntimeError(
            f"Secrets non résolus pour les champs suivants : {missing}. "
            "Vérifiez Vault, secrets.yaml ou les variables d'environnement."
        )
    return result


def _validate_llm_credentials(config: AgentConfig) -> None:
    settings = config.lm.planner
    if settings.provider != "anthropic":
        return

    if not settings.api_key or settings.api_key.startswith("${") or settings.api_key == "sk-ant-XXXX":
        raise ValueError(
            "Clé Anthropic manquante. Crée agent-recipe-creator/secrets.yaml "
            "depuis secrets.yaml.template ou exporte ANTHROPIC_API_KEY."
        )


def load_agent_config(
        config_path: Path,
        secrets_path: Path | None = None,
        secret_config_path: Path | None = None,
) -> AgentConfig:
    data = _load_yaml(config_path)
    data = _deep_merge(data, _load_secret_resolver_config(config_path, secret_config_path))
    secret_data = _load_yaml(secrets_path or config_path.with_name("secrets.yaml"))
    data = _expand_env(_deep_merge(data, secret_data))
    data = _resolve_config_secrets(data)
    config = AgentConfig.model_validate(data)
    _validate_llm_credentials(config)
    return config
