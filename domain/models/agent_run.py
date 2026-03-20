from typing import Literal

from arclith.domain.models.entity import Entity
from pydantic import Field

RunStatus = Literal["pending", "running", "success", "failed", "cancelled"]


class AgentRun(Entity):
    raw_input: str = Field(description = "Texte brut soumis à l'agent")
    status: RunStatus = Field(default = "pending", description = "Statut d'exécution du run")
    recipe_uuid: str | None = Field(default = None, description = "UUID de la recette créée dans le registre distant")
    recipe_name: str | None = Field(default = None, description = "Nom de la recette structurée")
    error: str | None = Field(default = None, description = "Message d'erreur si status=failed")
    metadata: dict = Field(
        default_factory = dict,
        description = "Données libres : timings, tokens, items résolus, …",
    )
