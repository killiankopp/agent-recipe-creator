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


def make_check_recipe_node(registry: _MCPRecipeRegistry, matcher: Callable) -> Callable:
    async def check_recipe_node(state: RecipeAgentState) -> dict:
        plan = state["plan"]
        logger.info(f"▶ [check_recipe] name={plan.name!r}")
        t0 = time.perf_counter()

        candidates = await registry.list_recipes(plan.name)
        match = matcher(plan.name, candidates)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        if match:
            logger.info(f"◀ [check_recipe] ♻️  already exists uuid={match['uuid']} in {elapsed_ms:.0f}ms")
            content = _format_response_existing(match)
            return {
                "recipe_exists": True,
                "recipe_uuid": match["uuid"],
                "messages": [{"role": "assistant", "content": content}],
            }

        logger.info(f"◀ [check_recipe] not found — will create in {elapsed_ms:.0f}ms")
        return {"recipe_exists": False}

    return check_recipe_node


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
        return {"recipe_uuid": created["uuid"]}

    return create_recipe_node


def make_link_ingredients_node(registry: _MCPRecipeRegistry) -> Callable:
    async def link_ingredients_node(state: RecipeAgentState) -> dict:
        recipe_uuid = state["recipe_uuid"]
        resolved = state["resolved_ingredients"]
        logger.info(f"▶ [link_ingredients] {len(resolved)} ingredient(s) → recipe {recipe_uuid}")
        t0 = time.perf_counter()

        for name, ingredient_uuid in resolved.items():
            result = await registry.link_ingredient_to_recipe(recipe_uuid, ingredient_uuid)
            if isinstance(result, dict) and "error" in result:
                logger.warning(f"  ⚠️ link failed name={name!r}: {result['error']}")
            else:
                logger.info(f"  🔗 linked ingredient name={name!r} uuid={ingredient_uuid}")

        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(f"◀ [link_ingredients] done in {elapsed_ms:.0f}ms")
        return {}

    return link_ingredients_node


def make_link_ustensils_node(registry: _MCPRecipeRegistry) -> Callable:
    async def link_ustensils_node(state: RecipeAgentState) -> dict:
        recipe_uuid = state["recipe_uuid"]
        resolved = state["resolved_ustensils"]
        logger.info(f"▶ [link_ustensils] {len(resolved)} ustensil(s) → recipe {recipe_uuid}")
        t0 = time.perf_counter()

        for name, ustensil_uuid in resolved.items():
            result = await registry.link_ustensil_to_recipe(recipe_uuid, ustensil_uuid)
            if isinstance(result, dict) and "error" in result:
                logger.warning(f"  ⚠️ link failed name={name!r}: {result['error']}")
            else:
                logger.info(f"  🔗 linked ustensil name={name!r} uuid={ustensil_uuid}")

        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(f"◀ [link_ustensils] done in {elapsed_ms:.0f}ms")
        return {}

    return link_ustensils_node


def make_create_steps_node(registry: _MCPRecipeRegistry) -> Callable:
    async def create_steps_node(state: RecipeAgentState) -> dict:
        plan = state["plan"]
        recipe_uuid = state["recipe_uuid"]
        logger.info(f"▶ [create_steps] {len(plan.steps)} step(s) → recipe {recipe_uuid}")
        t0 = time.perf_counter()

        for step in plan.steps:
            created = await registry.create_step(recipe_uuid, step.title, step.instruction)
            logger.info(f"  ✅ created step title={step.title!r} uuid={created['uuid']}")

        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(f"◀ [create_steps] done in {elapsed_ms:.0f}ms")

        content = _format_response(plan, recipe_uuid, state["resolved_ingredients"], state["resolved_ustensils"])
        return {"messages": [{"role": "assistant", "content": content}]}

    return create_steps_node


def _format_plan_meta(plan: RecipePlan) -> list[str]:
    meta: list[str] = []
    if plan.servings:
        meta.append(f"👥 {plan.servings}")
    if plan.prep_time_minutes:
        meta.append(f"⏱ Prépa : {plan.prep_time_minutes} min")
    if plan.cook_time_minutes:
        meta.append(f"🔥 Cuisson : {plan.cook_time_minutes} min")
    return meta


def _format_plan_ingredients(plan: RecipePlan) -> list[str]:
    lines: list[str] = []
    if not plan.ingredients:
        return lines
    lines.append("\n## 🥕 Ingrédients")
    for ing in plan.ingredients:
        parts = [p for p in (ing.quantity, ing.unit) if p]
        prefix = " ".join(parts)
        lines.append(f"- {'**' + prefix + '**  ' if prefix else ''}{ing.name}")
    return lines


def _format_plan_steps(plan: RecipePlan) -> list[str]:
    lines: list[str] = []
    if not plan.steps:
        return lines
    lines.append("\n## 📋 Étapes")
    for i, step in enumerate(plan.steps, 1):
        duration = f" _{step.duration_minutes} min_" if step.duration_minutes else ""
        lines.append(f"\n**{i}. {step.title}**{duration}")
        lines.append(step.instruction)
    return lines


def _format_response(
        plan: RecipePlan, uuid: str, resolved_ingredients: dict, resolved_ustensils: dict
) -> str:
    lines: list[str] = [f"✅ **{plan.name}** créée avec succès — 🆔 `{uuid}`"]
    if plan.description:
        lines.append(f"\n_{plan.description}_")
    meta = _format_plan_meta(plan)
    if meta:
        lines.append("  •  ".join(meta))
    lines.extend(_format_plan_ingredients(plan))
    if plan.ustensils:
        lines.append("\n## 🍳 Ustensiles")
        lines.extend(f"- {ust.name}" for ust in plan.ustensils)
    lines.extend(_format_plan_steps(plan))
    return "\n".join(lines)


def _format_existing_ingredients(ingredients: list[dict]) -> list[str]:
    lines: list[str] = []
    if not ingredients:
        return lines
    lines.append("\n## 🥕 Ingrédients")
    for ing in ingredients:
        unit = f" ({ing['unit']})" if ing.get("unit") else ""
        lines.append(f"- {ing['name']}{unit}")
    return lines


def _format_existing_steps(steps: list[dict]) -> list[str]:
    lines: list[str] = []
    if not steps:
        return lines
    lines.append("\n## 📋 Étapes")
    for i, step in enumerate(steps, 1):
        lines.append(f"\n**{i}. {step['name']}**")
        if step.get("description"):
            lines.append(step["description"])
    return lines


def _format_response_existing(recipe: dict) -> str:
    lines: list[str] = [f"ℹ️ **{recipe['name']}** existe déjà — 🆔 `{recipe['uuid']}`"]
    if recipe.get("description"):
        lines.append(f"\n_{recipe['description']}_")
    if recipe.get("nutriscore"):
        lines.append(f"🏷 Nutriscore : {recipe['nutriscore']}")
    lines.extend(_format_existing_ingredients(recipe.get("ingredients") or []))
    ustensils = recipe.get("ustensils") or []
    if ustensils:
        lines.append("\n## 🍳 Ustensiles")
        lines.extend(f"- {ust['name']}" for ust in ustensils)
    lines.extend(_format_existing_steps(recipe.get("steps") or []))
    return "\n".join(lines)
