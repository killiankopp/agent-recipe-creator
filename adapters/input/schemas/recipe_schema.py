from pydantic import BaseModel, Field


class AiCreateRequestSchema(BaseModel):
    raw_text: str = Field(
        ...,
        description = "Texte brut de la recette : copier/coller internet, OCR, saisie libre…",
        examples = ["Tarte tatin : 6 pommes, 150g beurre, 200g sucre…"],
        min_length = 10,
    )
    allow_duplicate: bool = Field(
        False,
        description = "Créer un doublon si une recette équivalente existe déjà.",
    )


class AiCreateResponseSchema(BaseModel):
    recipe_uuid: str = Field(description = "UUID de la recette créée ou de la recette existante à confirmer")
    recipe_name: str = Field(description = "Nom de la recette structurée par l'agent")
    formatted_response: str = Field(description = "Résumé Markdown de la recette créée")
    created: bool = Field(default = True, description = "Indique si une nouvelle recette a été créée")
    duplicate_confirmation_required: bool = Field(
        default = False,
        description = "Indique si l'utilisateur doit confirmer la création d'un doublon",
    )
    existing_recipe_uuid: str | None = Field(default = None, description = "UUID de la recette déjà existante")
    existing_recipe_name: str | None = Field(default = None, description = "Nom de la recette déjà existante")
