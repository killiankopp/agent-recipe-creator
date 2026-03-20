from datetime import datetime

from pydantic import BaseModel, Field


class AgentRunSchema(BaseModel):
    uuid: str = Field(description = "UUID du run")
    status: str = Field(description = "Statut : pending | running | success | failed | cancelled")
    raw_input: str = Field(description = "Texte soumis à l'agent")
    recipe_uuid: str | None = Field(default = None, description = "UUID de la recette créée")
    recipe_name: str | None = Field(default = None, description = "Nom de la recette")
    error: str | None = Field(default = None, description = "Message d'erreur si status=failed")
    metadata: dict = Field(default_factory = dict, description = "Données libres : timings, tokens, …")
    created_at: datetime = Field(description = "Date de création du run")
    updated_at: datetime = Field(description = "Date de dernière mise à jour")

    model_config = {"from_attributes": True}
