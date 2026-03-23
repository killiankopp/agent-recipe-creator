# agent-recipe-creator — Copilot Instructions

Agent IA (LangGraph + pydantic-ai) qui transforme du texte brut en recette structurée via les MCP tools de `recipe/`.
Lire `AGENTS.md` local.

## Règles spécifiques à ce repo

- Ne jamais importer du code de `recipe/` — toute interaction passe par MCP (`_MCPRecipeRegistry`).
- L'URL MCP est dans `config.yaml` (`mcp_registry.url`) — ne pas hardcoder.
- `ProcessRawRecipeUseCase` est le seul point d'entrée applicatif — ne pas appeler `RecipeAgentAdapter` directement.
- Les nœuds LangGraph vivent dans `_nodes.py` — chaque nœud est une factory `make_*_node()`.
- Tests >= 80 % de coverage : `uv run --frozen pytest --cov-fail-under=80`.

