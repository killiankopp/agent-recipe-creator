# SKILLS.md — `agent-recipe-creator/`

Recettes paramétriques pour les tâches récurrentes sur l'agent `agent-recipe-creator`.
Pour les tâches cross-repo, voir `../SKILLS.md` à la racine du workspace.

Format : chaque skill est identifiée `SK-A##` (A = Agent recipe creator), avec contexte, étapes, validation.

---

## SK-A01 — Ajouter un nœud au graphe LangGraph

**Contexte :** enrichir le pipeline agent (ex. validation post-création, enrichissement nutriscore).

### Étapes

1. **`adapters/output/recipe_agent/_state.py`**
    - Ajouter le(s) champ(s) nécessaire(s) dans `RecipeAgentState` (TypedDict)
    - Les champs accumulateurs utilisent `Annotated[list, operator.add]`

2. **`adapters/output/recipe_agent/_nodes.py`**
    - Écrire `make_my_node(deps...) -> Callable` :
      ```python
      def make_my_node(registry: _MCPRecipeRegistry) -> Callable:
          async def my_node(state: RecipeAgentState) -> dict:
              # lire state["..."]
              # appeler registry.my_tool(...)
              return {"key": value}  # uniquement les clés à modifier
          return my_node
      ```

3. **`adapters/output/recipe_agent/agent_adapter.py`**
    - Ajouter le nœud dans `_build_graph()` :
      ```python
      g.add_node("my_node", make_my_node(registry))
      g.add_edge("previous_node", "my_node")
      g.add_edge("my_node", "next_node")
      ```
    - Pour un branchement conditionnel : `g.add_conditional_edges("my_node", _route_fn, {"a": "node_a", "b": END})`

4. Si le nœud produit un nouveau champ dans `RecipeResult` : mettre à jour `domain/models/recipe.py` et
   `agent_adapter.py` → `process()`

### Validation

```bash
uv run --frozen python main_cli.py "recette de test simple"
uv run --frozen pytest -v -m "not e2e"
```

---

## SK-A02 — Ajouter un tool MCP dans `_mcp_registry.py`

**Contexte :** appeler un nouveau tool MCP de `recipe/` depuis l'agent.

### Étapes

1. **`adapters/output/recipe_agent/_mcp_registry.py`**
    - Ajouter une méthode publique :
      ```python
      async def my_new_tool(self, arg1: str, arg2: int | None = None) -> dict:
          return await self._call("my_new_tool", {"arg1": arg1, "arg2": arg2})
      ```
    - Le nom passé à `_call()` doit correspondre exactement au nom du tool dans `recipe/`

2. Utiliser la méthode dans le nœud LangGraph approprié (voir SK-A01)

### Validation

```bash
# Vérifier que le tool existe dans recipe/
cd recipe && uv run --frozen python -c "
from adapters.input.fastmcp.tools import register_tools
from arclith import Arclith
from pathlib import Path
a = Arclith(Path('config.yaml'))
mcp = a.fastmcp('test')
register_tools(mcp, a)
import asyncio
tools = asyncio.run(mcp.list_tools())
print([t.name for t in tools])
"
```

---

## SK-A03 — Changer le modèle LLM (local ou cloud)

**Contexte :** basculer entre Anthropic (cloud) et un LLM local (LM Studio / Ollama).

### Étapes

1. Éditer `config.yaml` :
   ```yaml
   lm:
     planner:
       provider: openai          # anthropic | openai
       model_name: qwen3-9b      # selon votre LLM
       base_url: http://127.0.0.1:1234/v1  # pour local seulement
       api_key: lm-studio        # factice pour local
   ```

2. `_PydanticAIPlanner` (`adapters/output/recipe_agent/_planner.py`) résout automatiquement le provider :
    - `anthropic` → `AnthropicModel` + `AnthropicProvider`
    - `openai` sans `base_url` → `OpenAIChatModel`
    - `openai` avec `base_url` → `OpenAIChatModel` avec profil local (`prompted`, pas de thinking tokens)

### Validation

```bash
uv run --frozen python main_cli.py "Soupe à l'oignon"
```

---

## SK-A04 — Ajuster le seuil de fuzzy matching

**Contexte :** l'agent crée trop de doublons (seuil trop haut) ou fusionne des ingrédients différents (seuil trop bas).

### Étapes

1. `config.yaml` : modifier `fuzzy.threshold` (défaut : 80, plage : 0–100)
    - Valeur haute (ex. 95) : moins de faux positifs, plus de créations
    - Valeur basse (ex. 60) : plus de réutilisation, risque de fusion incorrecte

2. La valeur est injectée dans `_make_fuzzy_matcher(threshold)` à la construction du graphe.

### Validation

```bash
uv run --frozen python main_cli.py "Tarte aux pommes"
# Vérifier dans les logs que "resolved_ingredients" contient bien les UUIDs attendus
```

---

## SK-A05 — Consulter l'historique des runs

**Contexte :** accéder aux `AgentRun` passés pour diagnostiquer des échecs.

### Via l'API REST (`:8006`)

```bash
# Liste tous les runs
curl http://localhost:8006/agent-runs

# Détail d'un run
curl http://localhost:8006/agent-runs/<uuid>
```

### Via MongoDB directement

```javascript
db["agent_runs"].find({ status: "failed" }).sort({ created_at: -1 }).limit(10)
```

### Champs utiles dans `AgentRun`

| Champ                           | Contenu                                                |
|---------------------------------|--------------------------------------------------------|
| `status`                        | `pending`, `running`, `success`, `failed`, `cancelled` |
| `raw_input`                     | Texte brut soumis à l'agent                            |
| `recipe_uuid`                   | UUID de la recette créée dans `recipe/`                |
| `error`                         | Message d'erreur si `status=failed`                    |
| `metadata.elapsed_ms`           | Durée d'exécution                                      |
| `metadata.resolved_ingredients` | Nombre d'ingrédients résolus                           |

