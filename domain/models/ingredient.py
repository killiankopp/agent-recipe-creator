from typing import Optional

from pydantic import Field, field_validator

from arclith.domain.models.entity import Entity


class Ingredient(Entity):
    name: str = Field(
        ...,
        description="Nom de l'ingrédient",
        examples=["Farine de blé", "Sel fin"],
    )
    unit: str | None = Field(
        default=None,
        description="Unité de mesure associée à l'ingrédient (ex. g, kg, ml). None si non applicable.",
        examples=["g", "kg", "ml", None],
    )

    @field_validator("name", mode="before")
    @classmethod
    def strip_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Ingredient name cannot be empty")
        return stripped

    @field_validator("unit", mode="before")
    @classmethod
    def strip_unit(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        stripped = v.strip()
        if not stripped:
            raise ValueError("Ingredient unit cannot be empty when provided")
        return stripped
