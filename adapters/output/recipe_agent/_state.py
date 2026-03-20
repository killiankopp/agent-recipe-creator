from typing import Annotated, TypedDict

from domain.models.recipe import RecipePlan
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class RecipeAgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    plan: RecipePlan | None
    resolved_ingredients: dict[str, str]  # name → uuid
    resolved_ustensils: dict[str, str]  # name → uuid
    recipe_uuid: str | None
    error: str | None
