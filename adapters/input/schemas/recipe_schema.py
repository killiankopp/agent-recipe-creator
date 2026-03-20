from pydantic import BaseModel, Field


class AiCreateRequestSchema(BaseModel):
    raw_text: str = Field(
        ...,
        description = "Texte brut de la recette : copier/coller internet, OCR, saisie libre…",
        examples = ["Tarte tatin : 6 pommes, 150g beurre, 200g sucre…"],
        min_length = 10,
    )


class AiCreateResponseSchema(BaseModel):
    recipe_uuid: str = Field(description = "UUID de la recette créée dans le registre")
    recipe_name: str = Field(description = "Nom de la recette structurée par l'agent")
    formatted_response: str = Field(description = "Résumé Markdown de la recette créée")
