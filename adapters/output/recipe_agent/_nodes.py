from collections.abc import Callable

import time
from adapters.output.recipe_agent._logger import log as logger
from adapters.output.recipe_agent._mcp_registry import _MCPRecipeRegistry
from adapters.output.recipe_agent._planner import _PydanticAIPlanner
from adapters.output.recipe_agent._state import RecipeAgentState
from domain.models.recipe import RecipePlan


def make_plan_node(planner: _PydanticAIPlanner) -> Callable:
    async def plan_node(state: RecipeAgentState) -> dict:
        user_message = state["messages"][-1].content
        logger.info(f"▶ [plan] length={len(user_message)} content={user_message[:200]!r}")
        t0 = time.perf_counter()

        plan = await planner.plan(user_message)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            f"◀ [plan] {elapsed_ms:.0f}ms — "
            f"name={plan.name!r} "
            f"ingredients={len(plan.ingredients)} "
            f"ustensils={len(plan.ustensils)}"
        )
        return {"plan": plan}

    return plan_node


def make_resolve_ingredients_node(registry: _MCPRecipeRegistry, matcher: Callable) -> Callable:
    async def resolve_ingredients_node(state: RecipeAgentState) -> dict:
        plan = state["plan"]
        logger.info(f"▶ [resolve_ingredients] {len(plan.ingredients)} ingredient(s)")
        t0 = time.perf_counter()
        resolved: dict[str, str] = {}

        for line in plan.ingredients:
            candidates = await registry.list_ingredients(line.name)
            match = matcher(line.name, candidates)
            if match:
                logger.info(f"  ♻️  reuse ingredient name={line.name!r} uuid={match['uuid']}")
                resolved[line.name] = match["uuid"]
            else:
                created = await registry.create_ingredient(line.name, line.unit)
                logger.info(f"  ✅ create ingredient name={line.name!r} unit={line.unit!r} uuid={created['uuid']}")
                resolved[line.name] = created["uuid"]

        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(f"◀ [resolve_ingredients] {len(resolved)} resolved in {elapsed_ms:.0f}ms")
        return {"resolved_ingredients": resolved}

    return resolve_ingredients_node


def make_resolve_ustensils_node(registry: _MCPRecipeRegistry, matcher: Callable) -> Callable:
    async def resolve_ustensils_node(state: RecipeAgentState) -> dict:
        plan = state["plan"]
        logger.info(f"▶ [resolve_ustensils] {len(plan.ustensils)} ustensil(s)")
        t0 = time.perf_counter()
        resolved: dict[str, str] = {}

        for line in plan.ustensils:
            candidates = await registry.list_ustensils(line.name)
            match = matcher(line.name, candidates)
            if match:
                logger.info(f"  ♻️  reuse ustensil name={line.name!r} uuid={match['uuid']}")
                resolved[line.name] = match["uuid"]
            else:
                created = await registry.create_ustensil(line.name)
                logger.info(f"  ✅ create ustensil name={line.name!r} uuid={created['uuid']}")
                resolved[line.name] = created["uuid"]

        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(f"◀ [resolve_ustensils] {len(resolved)} resolved in {elapsed_ms:.0f}ms")
        return {"resolved_ustensils": resolved}

    return resolve_ustensils_node


def make_create_recipe_node(registry: _MCPRecipeRegistry) -> Callable:
    async def create_recipe_node(state: RecipeAgentState) -> dict:
        plan = state["plan"]
        logger.info(f"▶ [create_recipe] name={plan.name!r}")
        t0 = time.perf_counter()

        created = await registry.create_recipe(plan.name, plan.description)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(f"◀ [create_recipe] 🎉 uuid={created['uuid']} in {elapsed_ms:.0f}ms")

        content = _format_response(
            plan, created["uuid"], state["resolved_ingredients"], state["resolved_ustensils"]
        )
        return {
            "recipe_uuid": created["uuid"],
            "messages": [{"role": "assistant", "content": content}],
        }

    return create_recipe_node


def _format_response(
        plan: RecipePlan, uuid: str, resolved_ingredients: dict, resolved_ustensils: dict
) -> str:
    lines: list[str] = [f"✅ **{plan.name}** créée avec succès — 🆔 `{uuid}`"]

    if plan.description:
        lines.append(f"\n_{plan.description}_")

    meta: list[str] = []
    if plan.servings:
        meta.append(f"👥 {plan.servings}")
    if plan.prep_time_minutes:
        meta.append(f"⏱ Prépa : {plan.prep_time_minutes} min")
    if plan.cook_time_minutes:
        meta.append(f"🔥 Cuisson : {plan.cook_time_minutes} min")
    if meta:
        lines.append("  •  ".join(meta))

    if plan.ingredients:
        lines.append("\n## 🥕 Ingrédients")
        for ing in plan.ingredients:
            parts = []
            if ing.quantity:
                parts.append(ing.quantity)
            if ing.unit:
                parts.append(ing.unit)
            prefix = " ".join(parts)
            lines.append(f"- {'**' + prefix + '**  ' if prefix else ''}{ing.name}")

    if plan.ustensils:
        lines.append("\n## 🍳 Ustensiles")
        for ust in plan.ustensils:
            lines.append(f"- {ust.name}")

    if plan.steps:
        lines.append("\n## 📋 Étapes")
        for i, step in enumerate(plan.steps, 1):
            duration = f" _{step.duration_minutes} min_" if step.duration_minutes else ""
            lines.append(f"\n**{i}. {step.title}**{duration}")
            lines.append(step.instruction)

    return "\n".join(lines)
