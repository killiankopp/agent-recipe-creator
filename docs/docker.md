# Docker — agent-recipe-creator

## Structure de l'image

Build multistage 2 étapes :

| Stage     | Base                        | Rôle                                                    |
|-----------|-----------------------------|---------------------------------------------------------|
| `builder` | `python:3.13-slim-bookworm` | Installe les dépendances de prod dans `/app/.venv`      |
| `runtime` | `python:3.13-slim-bookworm` | Image finale — venv + code source, sans outils de build |

Même image de base pour les deux stages → un seul pull Docker Hub, pas de dépendance ghcr.io.

**Pourquoi `uv export` + `pip install` plutôt que `uv sync` ?**

uv est toujours utilisé, mais uniquement pour lire le lockfile :

1. `uv export --frozen --no-emit-project` → lit `uv.lock` et génère un `requirements.txt` avec versions et hashes
   fixés (pur PyPI, sans référence à des chemins locaux)
2. `pip install -r requirements.txt` → installe les packages depuis PyPI

`uv sync` tente de résoudre l'arborescence du projet (workspace, chemins relatifs) ce qui échoue en environnement isolé.
`uv export` court-circuite cette résolution et garantit la même reproductibilité que le lockfile.

Le `config.yaml` n'est **jamais** intégré à l'image. Il est monté en lecture seule au démarrage du conteneur.

> **Prérequis :** le service `recipe` doit être démarré et accessible à l'URL configurée dans `mcp_registry.url`.

---

## Configuration locale

Les configs locales vivent dans `_configs/` à la racine des repos (gitignorées) :

```
_configs/
└── agent-recipe-creator/
    └── config.yaml   ← copié depuis agent-recipe-creator/config.yaml, à adapter
```

**Remplir obligatoirement dans `_configs/agent-recipe-creator/config.yaml` :**

- `lm.planner.api_key` — clé Anthropic (ou credentials du LLM local)
- `mcp_registry.url` — URL MCP du service `recipe` joignable depuis le conteneur

---

## Build

> Depuis la racine des repos (`…/Rekipe/` contenant `recipe/`, `agent-recipe-creator/`, `_configs/`)

```bash
docker build -t killiankopp/agent-recipe-creator agent-recipe-creator/
```

Rebuild propre après changement de dépendances (`pyproject.toml` / `uv.lock`) :

```bash
docker build --no-cache -t killiankopp/agent-recipe-creator agent-recipe-creator/
```

---

## Lancement

> Depuis la racine des repos.

```bash
# Raccourci local pour le montage config
CONFIG="-v $(pwd)/_configs/agent-recipe-creator/config.yaml:/app/config.yaml:ro"

# REST API  (port défini dans config.yaml → api.port)
docker run --rm $CONFIG -p 8006:8006 killiankopp/agent-recipe-creator python main_api.py

# CLI interactif
docker run --rm -it $CONFIG killiankopp/agent-recipe-creator python main_cli.py

# MCP SSE  (port défini dans config.yaml → mcp.port)
docker run --rm $CONFIG -p 8004:8004 killiankopp/agent-recipe-creator python main_mcp_sse.py

# MCP Streamable HTTP
docker run --rm $CONFIG -p 8004:8004 killiankopp/agent-recipe-creator python main_mcp_http.py

# MCP stdio
docker run --rm -i $CONFIG killiankopp/agent-recipe-creator python main_mcp_stdio.py
```

---

## Production

En production, ne pas monter un fichier bind-mount. Injecter la config (et notamment l'API key) via un **Docker secret**
ou un **ConfigMap Kubernetes**.

**Docker Swarm / standalone secret :**

```bash
# Créer le secret (une seule fois)
docker secret create agent-config _configs/agent-recipe-creator/config.yaml

# Lancer avec le secret
docker run --rm \
  --mount type=secret,id=agent-config,target=/app/config.yaml \
  -p 8006:8006 \
  killiankopp/agent-recipe-creator python main_api.py
```

**Kubernetes ConfigMap :**

```yaml
# Le ConfigMap est monté via volumeMounts[].mountPath: /app/config.yaml
# La clé API est injectée via un Secret séparé (pas dans le ConfigMap)
```

