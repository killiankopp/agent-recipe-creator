from abc import ABC, abstractmethod

from domain.models.recipe import RecipeResult


class RecipeAgentPort(ABC):
    @abstractmethod
    async def process(self, raw_text: str, run_uuid: str) -> RecipeResult: ...
