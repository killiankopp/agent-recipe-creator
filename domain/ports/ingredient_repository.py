from abc import abstractmethod

from arclith.domain.ports.repository import Repository
from domain.models.ingredient import Ingredient


class IngredientRepository(Repository[Ingredient]):
    @abstractmethod
    async def find_by_name(self, name: str) -> list[Ingredient]:
        pass
