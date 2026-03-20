import pytest
from uuid6 import uuid7

from application.services.ingredient_service import IngredientService
from domain.models.ingredient import Ingredient


@pytest.fixture
def service(repo, logger):
    return IngredientService(repo, logger)


async def test_create_and_read(service):
    ingredient = await service.create(Ingredient(name="Farine"))
    found = await service.read(ingredient.uuid)
    assert found is not None
    assert found.name == "Farine"


async def test_update(service):
    ingredient = await service.create(Ingredient(name="Farine"))
    updated = await service.update(ingredient.model_copy(update={"name": "Farine complète"}))
    assert updated.name == "Farine complète"
    assert updated.version == 2


async def test_delete_hides_from_read(service):
    ingredient = await service.create(Ingredient(name="Sel"))
    await service.delete(ingredient.uuid)
    assert await service.read(ingredient.uuid) is None


async def test_find_all(service):
    await service.create(Ingredient(name="Farine"))
    await service.create(Ingredient(name="Sel"))
    result = await service.find_all()
    assert len(result) == 2


async def test_find_by_name(service):
    await service.create(Ingredient(name="Farine de blé"))
    await service.create(Ingredient(name="Sel fin"))
    result = await service.find_by_name("farine")
    assert len(result) == 1
    assert result[0].name == "Farine de blé"


async def test_duplicate(service):
    ingredient = await service.create(Ingredient(name="Farine"))
    clone = await service.duplicate(ingredient.uuid)
    assert clone.uuid != ingredient.uuid
    assert clone.name == "Farine"


async def test_read_unknown_returns_none(service):
    assert await service.read(uuid7()) is None


async def test_find_by_name_no_results(service):
    await service.create(Ingredient(name="Sel"))
    result = await service.find_by_name("farine")
    assert result == []

