from application.services.ingredient_service import IngredientService
from arclith import Arclith
from arclith.adapters.output.mongodb.config import MongoDBConfig
from arclith.domain.ports.logger import Logger
from domain.ports.ingredient_repository import IngredientRepository


def build_ingredient_service(arclith: Arclith) -> tuple[IngredientService, Logger]:
    config = arclith.config
    repo: IngredientRepository
    arclith.logger.info("🗄️ Repository adapter selected", adapter = config.adapters.repository)
    match config.adapters.repository:
        case "mongodb":
            from adapters.output.mongodb.repository import MongoDBIngredientRepository
            mongo = config.adapters.mongodb
            if mongo is None:
                raise RuntimeError("MongoDB settings are required when repository=mongodb")
            repo = MongoDBIngredientRepository(
                MongoDBConfig(uri=mongo.uri, db_name=mongo.db_name),
                arclith.logger,
            )
        case "duckdb":
            from adapters.output.duckdb.repository import DuckDBIngredientRepository
            duckdb = config.adapters.duckdb
            if duckdb is None:
                raise RuntimeError("DuckDB settings are required when repository=duckdb")
            repo = DuckDBIngredientRepository(duckdb.path)
        case _:
            from adapters.output.memory.repository import InMemoryIngredientRepository
            repo = InMemoryIngredientRepository()
    return IngredientService(repo, arclith.logger, config.soft_delete.retention_days), arclith.logger

