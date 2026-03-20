import pytest
from datetime import datetime, timezone

from adapters.input.schemas.ingredient_schema import (
    IngredientCreateSchema,
    IngredientPatchSchema,
    IngredientSchema,
    IngredientUpdateSchema,
)
from domain.models.ingredient import Ingredient


# --- IngredientCreateSchema ---

def test_create_schema_valid():
    s = IngredientCreateSchema(name="Farine")
    assert s.name == "Farine"
    assert s.unit is None


def test_create_schema_with_unit():
    s = IngredientCreateSchema(name="Farine", unit="kg")
    assert s.unit == "kg"


def test_create_schema_empty_name_raises():
    with pytest.raises(Exception):
        IngredientCreateSchema(name="")


def test_create_schema_empty_unit_raises():
    with pytest.raises(Exception):
        IngredientCreateSchema(name="Farine", unit="")


# --- IngredientPatchSchema ---

def test_patch_schema_all_none():
    s = IngredientPatchSchema()
    assert s.name is None
    assert s.unit is None


def test_patch_schema_partial():
    s = IngredientPatchSchema(name="Farine complète")
    assert s.name == "Farine complète"


def test_patch_schema_empty_name_raises():
    with pytest.raises(Exception):
        IngredientPatchSchema(name="")


# --- IngredientUpdateSchema ---

def test_update_schema_valid():
    s = IngredientUpdateSchema(name="Sel fin")
    assert s.name == "Sel fin"


def test_update_schema_empty_name_raises():
    with pytest.raises(Exception):
        IngredientUpdateSchema(name="")


# --- IngredientSchema (response) ---

def test_ingredient_schema_from_entity():
    entity = Ingredient(name="Farine", unit="kg")
    schema = IngredientSchema.model_validate(entity)
    assert schema.name == "Farine"
    assert schema.unit == "kg"
    assert schema.is_deleted is False
    assert schema.version == 1


def test_ingredient_schema_deleted_entity():
    entity = Ingredient(name="Sel", deleted_at=datetime.now(timezone.utc))
    schema = IngredientSchema.model_validate(entity)
    assert schema.is_deleted is True


def test_ingredient_schema_uuid_serialized():
    entity = Ingredient(name="Farine")
    schema = IngredientSchema.model_validate(entity)
    assert str(schema.uuid) == str(entity.uuid)

