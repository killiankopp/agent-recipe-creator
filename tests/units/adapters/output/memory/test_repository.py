from datetime import datetime, timezone

import pytest
from uuid6 import uuid7

from domain.models.ingredient import Ingredient


async def test_create_and_read(repo):
    i = Ingredient(name="Farine")
    await repo.create(i)
    found = await repo.read(i.uuid)
    assert found is not None
    assert found.name == "Farine"


async def test_read_unknown_returns_none(repo):
    assert await repo.read(uuid7()) is None


async def test_find_by_name_match(repo):
    await repo.create(Ingredient(name="Farine de blé"))
    await repo.create(Ingredient(name="Sel fin"))
    result = await repo.find_by_name("farine")
    assert len(result) == 1
    assert result[0].name == "Farine de blé"


async def test_find_by_name_case_insensitive(repo):
    await repo.create(Ingredient(name="Farine"))
    assert len(await repo.find_by_name("FARINE")) == 1


async def test_find_by_name_includes_deleted(repo):
    deleted = Ingredient(name="Farine", deleted_at=datetime.now(timezone.utc))
    await repo.create(deleted)
    result = await repo.find_by_name("farine")
    assert len(result) == 1


async def test_find_by_name_empty(repo):
    assert await repo.find_by_name("inconnu") == []


async def test_find_all_excludes_deleted(repo):
    await repo.create(Ingredient(name="Farine"))
    deleted = Ingredient(name="Sel", deleted_at=datetime.now(timezone.utc))
    await repo.create(deleted)
    result = await repo.find_all()
    assert len(result) == 1
    assert result[0].name == "Farine"


async def test_duplicate(repo):
    i = await repo.create(Ingredient(name="Farine"))
    clone = await repo.duplicate(i.uuid)
    assert clone.uuid != i.uuid
    assert clone.name == "Farine"


async def test_duplicate_deleted_raises(repo):
    i = Ingredient(name="Farine", deleted_at=datetime.now(timezone.utc))
    await repo.create(i)
    with pytest.raises(KeyError):
        await repo.duplicate(i.uuid)

