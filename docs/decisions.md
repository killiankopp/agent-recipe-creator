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

## ADR-002 — Contrat `recipe/` centralisé dans `_MCPRecipeRegistry`

**Contexte :** Comment appeler les tools MCP de `recipe/` depuis le graphe LangGraph.

**Décision :** `_MCPRecipeRegistry` reste l'unique façade d'accès à `recipe/`. La configuration MCP est conservée,
mais les opérations critiques de création/lecture passent par l'API HTTP `recipe_api.url` pour rester alignées avec le
contrat V2 des recettes complètes et éviter les problèmes de boucle async observés avec le client MCP local.

**Pourquoi pas l'alternative évidente (appel HTTP direct vers l'API REST de `recipe/`) :**
Le graphe ne doit pas connaître les routes REST. L'appel HTTP est encapsulé dans `_MCPRecipeRegistry`, qui conserve les
noms d'opérations métier (`list_ingredients`, `create_recipe`, etc.) et isole le couplage technique dans un seul fichier.

**Conséquence sur le code :**

- `_MCPRecipeRegistry._call(tool_name, args)` est le seul point d'appel vers `recipe/`.
- L'URL MCP reste dans `config.yaml` → `mcp_registry.url`.
- L'URL HTTP est dans `config.yaml` → `recipe_api.url`.
- Le tenant est transmis via l'en-tête `X-Tenant-URI`.
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

## ADR-005 — Secrets LLM hors `config.yaml`

**Contexte :** Gestion de la clé API Anthropic/OpenAI.

**Décision actuelle :** `config.yaml` conserve uniquement une référence `${ANTHROPIC_API_KEY}`.
La clé réelle est résolue en priorité depuis Vault via `config/secrets.yaml`.
Le fallback local reste `secrets.yaml` non versionné, puis la variable d'environnement.

**Problème connu :** `config.yaml` est versionné dans Git — la clé ne doit jamais y être écrite.

**Règle locale :** écrire la clé dans Vault au chemin `kv/rekipe/agent-recipe-creator/anthropic`,
champ `value`. Pour un développement hors Vault, créer `agent-recipe-creator/secrets.yaml`
depuis `secrets.yaml.template` et renseigner `lm.planner.api_key`.

**Conséquence sur le code :**

- `config/secrets.yaml` mappe `lm.planner.api_key` vers `rekipe/agent-recipe-creator/anthropic`.
- `infrastructure/config.py` → `load_agent_config()` fusionne `config.yaml`, applique Vault/YAML et garde le fallback environnement.
- `.gitignore` exclut `secrets.yaml`.
