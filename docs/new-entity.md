# Ajouter une entité

Ce guide décrit les étapes pour intégrer une nouvelle entité dans le projet. Chaque étape correspond à une couche de l'architecture hexagonale.

L'exemple utilisé est `Recipe` (une recette).

---

## 1. Domain — Modèle

`domain/models/recipe.py`

```python
from typing import Optional
from pydantic import Field, field_validator
from arclith.domain.models.entity import Entity


class Recipe(Entity):
    name: str = Field(
        default="",
        min_length=1,
        description="Nom de la recette.",
        examples=["Quiche lorraine"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Description courte de la recette.",
        examples=["Une recette traditionnelle alsacienne.", None],
    )

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Recipe name cannot be empty")
        return stripped
```

---

## 2. Domain — Port repository

`domain/ports/recipe_repository.py`

```python
from abc import abstractmethod
from arclith.domain.ports.repository import Repository
from domain.models.recipe import Recipe


class RecipeRepository(Repository[Recipe]):
    @abstractmethod
    async def find_by_name(self, name: str) -> list[Recipe]:
        pass
```

---

## 3. Application — Use case spécifique

Si l'entité nécessite un use case propre (ex. recherche par nom) :

`application/use_cases/find_recipe_by_name.py`

```python
from domain.models.recipe import Recipe
from domain.ports.recipe_repository import RecipeRepository
from arclith.domain.ports.logger import Logger


class FindRecipeByNameUseCase:
    def __init__(self, repository: RecipeRepository, logger: Logger) -> None:
        self._repository = repository
        self._logger = logger

    async def execute(self, name: str) -> list[Recipe]:
        self._logger.info("🔍 Finding recipes by name", name=name)
        result = [r for r in await self._repository.find_by_name(name) if not r.is_deleted]
        self._logger.info("✅ Recipes found", name=name, count=len(result))
        return result
```

Exposer dans `application/use_cases/__init__.py` :

```python
from .find_recipe_by_name import FindRecipeByNameUseCase
```

---

## 4. Application — Service

`application/services/recipe_service.py`

```python
from arclith import BaseService, Logger
from domain.models.recipe import Recipe
from domain.ports.recipe_repository import RecipeRepository
from application.use_cases import FindRecipeByNameUseCase


class RecipeService(BaseService[Recipe]):
    def __init__(self, repository: RecipeRepository, logger: Logger, retention_days: float | None = None) -> None:
        super().__init__(repository, logger, retention_days)
        self._find_by_name_uc = FindRecipeByNameUseCase(repository, logger)

    async def find_by_name(self, name: str) -> list[Recipe]:
        return await self._find_by_name_uc.execute(name)
```

---

## 5. Adapters output — Repositories

### Memory

`adapters/output/memory/recipe_repository.py`

```python
from arclith.adapters.output.memory.repository import InMemoryRepository
from domain.models.recipe import Recipe
from domain.ports.recipe_repository import RecipeRepository


class InMemoryRecipeRepository(InMemoryRepository[Recipe], RecipeRepository):
    async def find_by_name(self, name: str) -> list[Recipe]:
        return [r for r in self._store.values() if name.lower() in r.name.lower()]
```

### MongoDB

`adapters/output/mongodb/recipe_repository.py`

```python
import re
from arclith.adapters.output.mongodb.config import MongoDBConfig
from arclith.adapters.output.mongodb.repository import MongoDBRepository
from arclith.domain.ports.logger import Logger
from domain.models.recipe import Recipe
from domain.ports.recipe_repository import RecipeRepository


class MongoDBRecipeRepository(MongoDBRepository[Recipe], RecipeRepository):
    def __init__(self, config: MongoDBConfig, logger: Logger) -> None:
        super().__init__(config, Recipe, logger)

    async def find_by_name(self, name: str) -> list[Recipe]:
        async with self._collection() as col:
            escaped = re.escape(name)
            return [
                self._from_doc(doc)
                async for doc in col.find(
                    {"name": {"$regex": escaped, "$options": "i"}, "deleted_at": None}
                )
            ]
```

### DuckDB

`adapters/output/duckdb/recipe_repository.py`

```python
from arclith.adapters.output.duckdb.repository import DuckDBRepository
from domain.models.recipe import Recipe
from domain.ports.recipe_repository import RecipeRepository


class DuckDBRecipeRepository(DuckDBRepository[Recipe], RecipeRepository):
    def __init__(self, path: str) -> None:
        super().__init__(path, Recipe)

    async def find_by_name(self, name: str) -> list[Recipe]:
        rows = self._fetch(
            f"SELECT * FROM {self._table} WHERE deleted_at IS NULL AND lower(name) LIKE ?",
            [f"%{name.lower()}%"],
        )
        return [self._row_to_entity(r) for r in rows]
```

---

## 6. Adapters input — Schémas

`adapters/input/schemas/recipe_schema.py`

```python
from typing import Optional
from pydantic import BaseModel, Field
from arclith.adapters.input.schemas.base_schema import BaseSchema


class RecipeCreateSchema(BaseModel):
    name: str = Field(min_length=1, description="Nom de la recette.", examples=["Quiche lorraine"])
    description: Optional[str] = Field(default=None, description="Description courte.", examples=["Une recette traditionnelle.", None])


class RecipePatchSchema(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, description="Nouveau nom.", examples=["Quiche alsacienne", None])
    description: Optional[str] = Field(default=None, description="Nouvelle description.", examples=[None])


class RecipeUpdateSchema(BaseModel):
    name: str = Field(min_length=1, description="Nom de la recette.", examples=["Quiche lorraine"])
    description: Optional[str] = Field(default=None, description="Description courte.", examples=[None])


class RecipeSchema(BaseSchema):
    name: str = Field(description="Nom de la recette.", examples=["Quiche lorraine"])
    description: Optional[str] = Field(default=None, description="Description courte.", examples=[None])
```

---

## 7. Adapters input — Router FastAPI

`adapters/input/fastapi/recipe_router.py`

Copier `ingredient_router.py`, remplacer `Ingredient` → `Recipe` et adapter les champs.

Puis enregistrer dans `adapters/input/fastapi/router.py` :

```python
from infrastructure.recipe_container import build_recipe_service
from adapters.input.fastapi.recipe_router import RecipeRouter

def register_routers(app: FastAPI, arclith: Arclith) -> None:
    ...
    service, logger = build_recipe_service(arclith)
    app.include_router(RecipeRouter(service, logger).router)
```

---

## 8. Adapters input — Tools FastMCP

`adapters/input/fastmcp/recipe_tools.py`

Copier `ingredient_tools.py`, remplacer `Ingredient` → `Recipe` et adapter les champs.

Puis enregistrer dans `adapters/input/fastmcp/tools.py` :

```python
from infrastructure.recipe_container import build_recipe_service
from adapters.input.fastmcp.recipe_tools import RecipeMCP

def register_tools(mcp: fastmcp.FastMCP, arclith: Arclith) -> None:
    ...
    service, logger = build_recipe_service(arclith)
    RecipeMCP(service, logger, mcp)
```

---

## 9. Infrastructure — Container

`infrastructure/recipe_container.py`

```python
from arclith import Arclith
from arclith.adapters.output.mongodb.config import MongoDBConfig
from arclith.domain.ports.logger import Logger
from application.services.recipe_service import RecipeService


def build_recipe_service(arclith: Arclith) -> tuple[RecipeService, Logger]:
    config = arclith.config
    match config.adapters.repository:
        case "mongodb":
            from adapters.output.mongodb.recipe_repository import MongoDBRecipeRepository
            mongo = config.adapters.mongodb
            repo = MongoDBRecipeRepository(MongoDBConfig(uri=mongo.uri, db_name=mongo.db_name), arclith.logger)
        case "duckdb":
            from adapters.output.duckdb.recipe_repository import DuckDBRecipeRepository
            repo = DuckDBRecipeRepository(config.adapters.duckdb.path)
        case _:
            from adapters.output.memory.recipe_repository import InMemoryRecipeRepository
            repo = InMemoryRecipeRepository()
    return RecipeService(repo, arclith.logger, config.soft_delete.retention_days), arclith.logger
```

Puis exposer dans `infrastructure/container.py` :

```python
from infrastructure.recipe_container import build_recipe_service
```

---

## Checklist

- [ ] `domain/models/recipe.py`
- [ ] `domain/ports/recipe_repository.py`
- [ ] `application/use_cases/find_recipe_by_name.py` + `__init__.py`
- [ ] `application/services/recipe_service.py`
- [ ] `adapters/output/memory/recipe_repository.py`
- [ ] `adapters/output/mongodb/recipe_repository.py`
- [ ] `adapters/output/duckdb/recipe_repository.py`
- [ ] `adapters/input/schemas/recipe_schema.py`
- [ ] `adapters/input/fastapi/recipe_router.py` + `router.py`
- [ ] `adapters/input/fastmcp/recipe_tools.py` + `tools.py`
- [ ] `infrastructure/recipe_container.py` + `container.py`

