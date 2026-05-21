from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from domain.models.recipe import RecipePlan


class RecipeAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    plan: RecipePlan | None
    resolved_ingredients: dict[str, str]  # name → uuid
    resolved_ustensils: dict[str, str]  # name → uuid
    resolved_components: list[dict]
    recipe_uuid: str | None
    recipe_exists: bool | None
    allow_duplicate: bool
    existing_recipe_uuid: str | None
    existing_recipe_name: str | None
    error: str | None
