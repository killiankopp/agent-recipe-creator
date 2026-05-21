import pytest
from pydantic import ValidationError

from adapters.input.schemas.recipe_schema import AiCreateRequestSchema, AiCreateResponseSchema


def test_ai_create_request_valid():
    schema = AiCreateRequestSchema(raw_text = "Voici une longue recette de gâteau au chocolat")
    assert schema.raw_text == "Voici une longue recette de gâteau au chocolat"
    assert schema.allow_duplicate is False


def test_ai_create_request_accepts_allow_duplicate():
    schema = AiCreateRequestSchema(
        raw_text = "Voici une longue recette de gâteau au chocolat",
        allow_duplicate = True,
    )
    assert schema.allow_duplicate is True


def test_ai_create_request_too_short():
    with pytest.raises(ValidationError):
        AiCreateRequestSchema(raw_text = "court")


def test_ai_create_request_exactly_min_length():
    schema = AiCreateRequestSchema(raw_text = "1234567890")
    assert len(schema.raw_text) == 10


def test_ai_create_request_below_min_length():
    with pytest.raises(ValidationError):
        AiCreateRequestSchema(raw_text = "123456789")  # 9 chars


def test_ai_create_response():
    schema = AiCreateResponseSchema(
        recipe_uuid = "r-uuid",
        recipe_name = "Gâteau au chocolat",
        formatted_response = "✅ Gâteau créé avec succès",
    )
    assert schema.recipe_uuid == "r-uuid"
    assert schema.recipe_name == "Gâteau au chocolat"
    assert "Gâteau" in schema.formatted_response
    assert schema.created is True
    assert schema.duplicate_confirmation_required is False


def test_ai_create_response_duplicate_confirmation():
    schema = AiCreateResponseSchema(
        recipe_uuid = "existing-r",
        recipe_name = "Gâteau au chocolat",
        formatted_response = "Aucune modification n'a été appliquée.",
        created = False,
        duplicate_confirmation_required = True,
        existing_recipe_uuid = "existing-r",
        existing_recipe_name = "Gâteau au chocolat",
    )
    assert schema.created is False
    assert schema.duplicate_confirmation_required is True
    assert schema.existing_recipe_uuid == "existing-r"


def test_ai_create_response_required_fields():
    with pytest.raises(ValidationError):
        AiCreateResponseSchema(recipe_uuid = "r-uuid")  # type: ignore[call-arg]
