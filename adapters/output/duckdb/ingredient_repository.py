from arclith.adapters.output.duckdb.repository import DuckDBRepository
from domain.models.ingredient import Ingredient
from domain.ports.ingredient_repository import IngredientRepository


class DuckDBIngredientRepository(DuckDBRepository[Ingredient], IngredientRepository):
    def __init__(self, path: str) -> None:
        super().__init__(path, Ingredient)

    # noinspection SqlNoDataSourceInspection
    async def find_by_name(self, name: str) -> list[Ingredient]:
        rows = self._fetch(
            f"SELECT * FROM {self._table} WHERE deleted_at IS NULL AND lower(name) LIKE ?",  # nosec B608
            [f"%{name.lower()}%"],
        )
        return [self._row_to_entity(r) for r in rows]
