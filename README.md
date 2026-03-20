# framework

## Architecture

**domain/models/**
Entités et objets valeur du domaine métier (ex: Recipe, Ingredient) — aucune dépendance extérieure

**domain/ports/**
Interfaces abstraites (ABC) définissant les contrats entre le domaine et le monde extérieur

**domain/services/**
Services métier purs qui orchestrent la logique domaine sans toucher l'infrastructure

**application/use_cases/**
Cas d'usage applicatifs — orchestrent les ports et services pour répondre à une intention utilisateur

**adapters/input/**
Adaptateurs entrants — traduisent une requête externe (CLI, HTTP, événement…) en appel de cas d'usage

**adapters/output/**
Adaptateurs sortants — implémentent les ports de sortie (base de données, API tierce, fichier…)

**infrastructure/**
Câblage global — instanciation et injection des dépendances, configuration, point d'entrée de l'app

---

## Lancement

### Prérequis

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 1. API REST (FastAPI)

Expose un CRUD HTTP sur les ingrédients.

```bash
python main_api.py
```

- Swagger UI : [http://localhost:8000/docs](http://localhost:8000/docs)
- Base URL : `http://localhost:8000/ingredient/v1/`

### 2. Serveur MCP stdio

Utilisé par les clients MCP locaux (Claude Desktop, Cursor…). Le client lance le process lui-même.

```bash
python main_mcp_stdio.py
```

Configuration `mcp.json` :

```json
{
  "mcpServers": {
    "rekipe-ingredients": {
      "command": "/chemin/vers/.venv/bin/python",
      "args": ["/chemin/vers/framework/main_mcp_stdio.py"]
    }
  }
}
```

### 3. Serveur MCP SSE

Expose les outils MCP via HTTP SSE. Le serveur doit tourner avant que le client s'y connecte.  
Tourne sur le port **8000**

```bash
python main_mcp_sse.py
```

- SSE endpoint : `http://localhost:8001/sse`
- Messages endpoint : `http://localhost:8001/messages/`

Configuration `mcp.json` :

```json
{
  "mcpServers": {
    "rekipe-ingredients-sse": {
      "url": "http://localhost:8000/sse"
    }
  }
}
```

> **Note** : les serveurs MCP (stdio et SSE) partagent la même instance `create_mcp()` définie dans `infrastructure/mcp.py`. Ajouter un nouveau transport ne nécessite aucune modification du domaine.

---

## Passer de InMemory à MongoDB

Par défaut, les trois points d'entrée (`main_api.py`, `main_mcp.py`, `main_mcp_sse.py`) utilisent `InMemoryIngredientRepository` — les données sont perdues à chaque redémarrage.

Pour persister les données dans MongoDB, remplace dans `infrastructure/api.py` et/ou `infrastructure/mcp.py` :

```python
# Avant
from adapters.output.in_memory_ingredient_repository import InMemoryIngredientRepository
ingredient_repository = InMemoryIngredientRepository()

# Après
from adapters.output.mongodb_config import MongoDBConfig
from adapters.output.mongodb_ingredient_repository import MongoDBIngredientRepository

config = MongoDBConfig(
    uri="mongodb://localhost:27017",
    db_name="rekipe",
    collection_name="ingredients"
)
ingredient_repository = MongoDBIngredientRepository(config)
```

`MongoDBConfig` accepte n'importe quelle connection string — tu peux ainsi viser une instance locale, Atlas, ou une instance par tenant en passant un `uri` différent.

Seule la ligne d'instanciation change dans `infrastructure/` : le domaine, les services et les cas d'usage n'ont aucune connaissance de MongoDB.

