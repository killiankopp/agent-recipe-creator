from adapters.output.recipe_agent._fuzzy import _make_fuzzy_matcher
from adapters.output.recipe_agent._mcp_registry import _MCPRecipeRegistry
from adapters.output.recipe_agent._nodes import (
    make_create_recipe_node,
    make_plan_node,
    make_resolve_ingredients_node,
    make_resolve_ustensils_node,
)
from adapters.output.recipe_agent._planner import _PydanticAIPlanner
from adapters.output.recipe_agent._state import RecipeAgentState
from domain.models.recipe import RecipeResult
from domain.ports.recipe_agent import RecipeAgentPort
from infrastructure.config import AgentConfig
from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph


def _build_graph(planner: _PydanticAIPlanner, registry: _MCPRecipeRegistry, matcher):
    g = StateGraph(RecipeAgentState)
    g.add_node("plan", make_plan_node(planner))
    g.add_node("resolve_ingredients", make_resolve_ingredients_node(registry, matcher))
    g.add_node("resolve_ustensils", make_resolve_ustensils_node(registry, matcher))
    g.add_node("create_recipe", make_create_recipe_node(registry))
    g.set_entry_point("plan")
    g.add_edge("plan", "resolve_ingredients")
    g.add_edge("resolve_ingredients", "resolve_ustensils")
    g.add_edge("resolve_ustensils", "create_recipe")
    g.add_edge("create_recipe", END)
    return g.compile()


class RecipeAgentAdapter(RecipeAgentPort):
    def __init__(self, config: AgentConfig) -> None:
        planner = _PydanticAIPlanner(config.lm.planner)
        registry = _MCPRecipeRegistry(config.mcp_registry.url)
        matcher = _make_fuzzy_matcher(config.fuzzy.threshold)
        self._graph = _build_graph(planner, registry, matcher)

    async def process(self, raw_text: str, run_uuid: str) -> RecipeResult:
        initial_state: RecipeAgentState = {
            "messages": [HumanMessage(content = raw_text)],
            "plan": None,
            "resolved_ingredients": {},
            "resolved_ustensils": {},
            "recipe_uuid": None,
            "error": None,
        }
        result = await self._graph.ainvoke(initial_state)
        last_message = result["messages"][-1]
        return RecipeResult(
            recipe_uuid = result["recipe_uuid"],
            recipe_name = result["plan"].name,
            resolved_ingredients = result["resolved_ingredients"],
            resolved_ustensils = result["resolved_ustensils"],
            formatted_response = last_message.content if hasattr(last_message, "content") else str(last_message),
        )
