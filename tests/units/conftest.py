from typing import Any
import pytest
from adapters.output.memory.repository import InMemoryIngredientRepository
from arclith.domain.ports.logger import Logger, LogLevel


class NullLogger(Logger):
    def __init__(self) -> None:
        self.records: list[dict] = []

    def log(self, level: LogLevel, message: str, **metadata: Any) -> None:
        self.records.append({"level": level, "message": message, "metadata": metadata})


@pytest.fixture
def logger() -> NullLogger:
    return NullLogger()


@pytest.fixture
def repo() -> InMemoryIngredientRepository:
    return InMemoryIngredientRepository()

