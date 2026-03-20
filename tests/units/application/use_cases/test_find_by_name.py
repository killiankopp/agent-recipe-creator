from application.use_cases import FindByNameUseCase
from domain.models.ingredient import Ingredient


async def test_find_by_name_returns_match(repo, logger):
    await repo.create(Ingredient(name="Farine de blé"))
    await repo.create(Ingredient(name="Sel fin"))
    result = await FindByNameUseCase(repo, logger).execute("farine")
    assert len(result) == 1
    assert result[0].name == "Farine de blé"


async def test_find_by_name_case_insensitive(repo, logger):
    await repo.create(Ingredient(name="Farine"))
    result = await FindByNameUseCase(repo, logger).execute("FARINE")
    assert len(result) == 1


async def test_find_by_name_partial_match(repo, logger):
    await repo.create(Ingredient(name="Farine de blé"))
    await repo.create(Ingredient(name="Farine complète"))
    result = await FindByNameUseCase(repo, logger).execute("farine")
    assert len(result) == 2


async def test_find_by_name_excludes_deleted(repo, logger):
    from datetime import datetime, timezone
    deleted = Ingredient(name="Farine", deleted_at=datetime.now(timezone.utc))
    await repo.create(deleted)
    result = await FindByNameUseCase(repo, logger).execute("farine")
    assert len(result) == 0


async def test_find_by_name_no_match(repo, logger):
    await repo.create(Ingredient(name="Sel"))
    result = await FindByNameUseCase(repo, logger).execute("farine")
    assert result == []

