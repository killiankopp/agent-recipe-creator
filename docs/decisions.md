# docs/decisions.md — `agent-recipe-creator/`

## ADR-001 — LangGraph comme orchestrateur du pipeline agent

**Contexte :** Choix du framework d'orchestration pour le pipeline de création de recettes.

**Décision :** LangGraph (`langgraph>=0.4.0`) avec un `StateGraph` compilé dans `agent_adapter.py`.

**Pourquoi pas l'alternative évidente (pydantic-ai seul) :**
pydantic-ai excelle pour les appels LLM structurés (un aller-retour avec un modèle de sortie typé), mais ne gère pas
l'orchestration multi-étapes avec état partagé. LangGraph modélise explicitement le graphe d'exécution, permet le
branchement conditionnel (`check_recipe` → `exists|new`) et maintient un `state` typé entre les nœuds.

**Conséquence sur le code :**

- `RecipeAgentState` (TypedDict) est le contrat entre tous les nœuds.
- Chaque nœud retourne uniquement les clés du state à modifier (merge partiel).
- `agent_adapter.py` est le seul fichier qui connaît la topologie du graphe.

---

## ADR-002 — `langchain-mcp-adapters` comme proxy MCP

**Contexte :** Comment appeler les tools MCP de `recipe/` depuis le graphe LangGraph.

**Décision :** `MultiServerMCPClient` de `langchain-mcp-adapters`, encapsulé dans `_MCPRecipeRegistry`.

**Pourquoi pas l'alternative évidente (appel HTTP direct vers l'API REST de `recipe/`) :**
Les tools MCP exposent une interface normalisée avec descriptions et schémas. `langchain-mcp-adapters` gère le protocole
MCP, la sérialisation et la liste des tools disponibles. Appeler l'API REST directement contournerait le contrat MCP et
créerait un couplage fort sur les routes REST.

**Conséquence sur le code :**

- `_MCPRecipeRegistry._call(tool_name, args)` est le seul point d'appel vers `recipe/`.
- L'URL MCP est dans `config.yaml` → `mcp_registry.url`.
- Le client est instancié une seule fois dans `RecipeAgentAdapter.__init__`.

---

## ADR-003 — `rapidfuzz` pour la résolution d'entités existantes

**Contexte :** Éviter les doublons dans `recipe/` quand l'agent crée des ingrédients et ustensiles.

**Décision :** `rapidfuzz` avec un seuil configurable (`fuzzy.threshold`, défaut 80). Si le score de similarité est ≥
seuil, l'entité existante est réutilisée ; sinon, elle est créée.

**Pourquoi pas l'alternative évidente (comparaison exacte) :**
Les LLM normalisent différemment selon les sessions ("farine de blé" vs "Farine blé"). Une comparaison exacte génèrerait
des doublons. Le fuzzy matching tolère les variations mineures tout en restant configurable.

**Conséquence sur le code :**

- `_make_fuzzy_matcher(threshold)` retourne une fonction `(query, candidates) -> dict | None`.
- `candidates` est la liste des entités retournées par `list_ingredients(name)` ou `list_ustensils(name)`.
- Le matcher est injecté dans `make_check_recipe_node`, `make_resolve_ingredients_node`, `make_resolve_ustensils_node`.

---

## ADR-004 — `AgentRun` comme entité de traçabilité persistée

**Contexte :** Comment tracer les exécutions de l'agent pour le debugging et l'audit.

**Décision :** `AgentRun` est une entité `arclith` persistée dans MongoDB (`agent-recipe-creator` collection
`agent_runs`). Créée avant l'exécution, mise à jour après (success ou failed).

**Pourquoi pas l'alternative évidente (logs applicatifs seulement) :**
Les logs sont éphémères et non structurés. `AgentRun` est queryable via l'API REST (`GET /agent-runs`), permet de
retracer chaque exécution avec son input brut, son résultat et ses timings. Utile pour identifier les patterns d'échec
et mesurer les performances.

**Conséquence sur le code :**

- `ProcessRawRecipeUseCase` encapsule la logique de création/mise à jour du run.
- `AgentRun.metadata` contient `elapsed_ms`, `resolved_ingredients`, `resolved_ustensils`.
- En cas d'erreur, `status=failed` et `error=str(exc)` sont persistés avant de re-raise.

---

## ADR-005 — Secrets LLM dans `config.yaml` (temporaire)

**Contexte :** Gestion de la clé API Anthropic/OpenAI.

**Décision actuelle :** La clé API est dans `config.yaml` (`lm.planner.api_key`).

**Problème connu :** `config.yaml` est versionné dans Git — la clé ne doit PAS être committée.

**Migration recommandée :**
Remplacer la valeur dans `config.yaml` par `${ANTHROPIC_API_KEY}` et résoudre via `os.environ` dans
`load_agent_config()`, ou utiliser un vault (HashiCorp Vault, AWS Secrets Manager).

**Conséquence sur le code :**

- `infrastructure/config.py` → `load_agent_config()` doit interpoler les variables d'environnement.
- `.gitignore` doit exclure `config.yaml` ou un fichier `config.local.yaml` doit être utilisé pour les secrets.

