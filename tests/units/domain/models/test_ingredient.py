import pytest
from domain.models.ingredient import Ingredient


def test_valid_ingredient():
    i = Ingredient(name="Farine")
    assert i.name == "Farine"
    assert i.unit is None


def test_name_stripped():
    i = Ingredient(name="  Sel fin  ")
    assert i.name == "Sel fin"


def test_empty_name_raises():
    with pytest.raises(Exception):
        Ingredient(name="")


def test_blank_name_raises():
    with pytest.raises(Exception):
        Ingredient(name="   ")


def test_unit_stripped():
    i = Ingredient(name="Farine", unit="  kg  ")
    assert i.unit == "kg"


def test_unit_none_allowed():
    i = Ingredient(name="Farine", unit=None)
    assert i.unit is None


def test_blank_unit_raises():
    with pytest.raises(Exception):
        Ingredient(name="Farine", unit="   ")


def test_inherits_entity_fields():
    from uuid6 import UUID
    i = Ingredient(name="Sel")
    assert isinstance(i.uuid, UUID)
    assert i.version == 1
    assert not i.is_deleted


def test_model_copy_update():
    i = Ingredient(name="Farine")
    copy = i.model_copy(update={"name": "Farine complète"})
    assert copy.name == "Farine complète"
    assert copy.uuid == i.uuid

