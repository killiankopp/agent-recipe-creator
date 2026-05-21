from collections.abc import Callable

import re
import time

from adapters.output.recipe_agent._logger import log as logger
from adapters.output.recipe_agent._mcp_registry import _MCPRecipeRegistry
from adapters.output.recipe_agent._planner import _PydanticAIPlanner
from adapters.output.recipe_agent._state import RecipeAgentState
from domain.models.recipe import RecipeComponentPlan, RecipePlan

type RecipePlanLike = RecipePlan | RecipeComponentPlan


def make_plan_node(planner: _PydanticAIPlanner) -> Callable:
    async def plan_node(state: RecipeAgentState) -> dict:
        user_message = state["messages"][-1].content
        assert isinstance(user_message, str)
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


def make_review_plan_node(planner: _PydanticAIPlanner) -> Callable:
    async def review_plan_node(state: RecipeAgentState) -> dict:
        plan = state["plan"]
        assert plan is not None
        user_message = state["messages"][0].content
        assert isinstance(user_message, str)
        logger.info(f"▶ [review_plan] name={plan.name!r}")
        t0 = time.perf_counter()

        reviewed = await planner.review(user_message, plan)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(
            f"◀ [review_plan] {elapsed_ms:.0f}ms — "
            f"ingredients={len(reviewed.ingredients)} "
            f"components={len(reviewed.components)}"
        )
        return {"plan": reviewed}

    return review_plan_node


def make_check_recipe_node(registry: _MCPRecipeRegistry, matcher: Callable) -> Callable:
    async def check_recipe_node(state: RecipeAgentState) -> dict:
        plan = state["plan"]
        assert plan is not None
        logger.info(f"▶ [check_recipe] name={plan.name!r}")
        t0 = time.perf_counter()

        candidates = await registry.list_recipes(plan.name)
        match = matcher(plan.name, candidates)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        if match:
            if state["allow_duplicate"]:
                logger.info(
                    f"◀ [check_recipe] duplicate allowed for existing uuid={match['uuid']} "
                    f"in {elapsed_ms:.0f}ms"
                )
                return {
                    "recipe_exists": False,
                    "existing_recipe_uuid": match["uuid"],
                    "existing_recipe_name": match["name"],
                }
            logger.info(f"◀ [check_recipe] duplicate confirmation required uuid={match['uuid']} in {elapsed_ms:.0f}ms")
            content = _format_response_duplicate_confirmation(match)
            return {
                "recipe_exists": True,
                "recipe_uuid": match["uuid"],
                "existing_recipe_uuid": match["uuid"],
                "existing_recipe_name": match["name"],
                "messages": [{"role": "assistant", "content": content}],
            }

        logger.info(f"◀ [check_recipe] not found — will create in {elapsed_ms:.0f}ms")
        return {"recipe_exists": False}

    return check_recipe_node


async def _resolve_ingredients_for_plan(
        plan: RecipePlanLike,
        registry: _MCPRecipeRegistry,
        matcher: Callable,
) -> dict[str, str]:
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
    return resolved


async def _resolve_ustensils_for_plan(
        plan: RecipePlanLike,
        registry: _MCPRecipeRegistry,
        matcher: Callable,
) -> dict[str, str]:
    resolved: dict[str, str] = {}
    for line in plan.ustensils:
        candidates = await registry.list_equipment(line.name)
        match = matcher(line.name, candidates)
        if match:
            logger.info(f"  ♻️  reuse ustensil name={line.name!r} uuid={match['uuid']}")
            resolved[line.name] = match["uuid"]
        else:
            created = await registry.create_equipment(line.name)
            logger.info(f"  ✅ create ustensil name={line.name!r} uuid={created['uuid']}")
            resolved[line.name] = created["uuid"]
    return resolved


def make_create_components_node(registry: _MCPRecipeRegistry, matcher: Callable) -> Callable:
    async def create_components_node(state: RecipeAgentState) -> dict:
        plan = state["plan"]
        assert plan is not None
        if not plan.components:
            return {"resolved_components": []}

        logger.info(f"▶ [create_components] {len(plan.components)} component(s)")
        t0 = time.perf_counter()
        resolved_components: list[dict] = []
        for rank, component in enumerate(plan.components, 1):
            candidates = await registry.list_recipes(component.name)
            match = matcher(component.name, candidates)
            if match:
                child_uuid = match["uuid"]
                logger.info(f"  ♻️  reuse component name={component.name!r} uuid={child_uuid}")
            else:
                component_ingredients = await _resolve_ingredients_for_plan(component, registry, matcher)
                component_ustensils = await _resolve_ustensils_for_plan(component, registry, matcher)
                created = await registry.create_recipe(
                    _build_recipe_payload(component, component_ingredients, component_ustensils)
                )
                child_uuid = created["uuid"]
                logger.info(f"  ✅ create component name={component.name!r} uuid={child_uuid}")

            resolved_components.append({
                "recipe_uuid": child_uuid,
                "label": component.name,
                "rank": rank,
                "servings_multiplier": component.servings_multiplier,
            })

        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(f"◀ [create_components] {len(resolved_components)} resolved in {elapsed_ms:.0f}ms")
        return {"resolved_components": resolved_components}

    return create_components_node


def make_resolve_ingredients_node(registry: _MCPRecipeRegistry, matcher: Callable) -> Callable:
    async def resolve_ingredients_node(state: RecipeAgentState) -> dict:
        plan = state["plan"]
        assert plan is not None
        logger.info(f"▶ [resolve_ingredients] {len(plan.ingredients)} ingredient(s)")
        t0 = time.perf_counter()
        resolved = {} if plan.components else await _resolve_ingredients_for_plan(plan, registry, matcher)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(f"◀ [resolve_ingredients] {len(resolved)} resolved in {elapsed_ms:.0f}ms")
        return {"resolved_ingredients": resolved}

    return resolve_ingredients_node


def make_resolve_ustensils_node(registry: _MCPRecipeRegistry, matcher: Callable) -> Callable:
    async def resolve_ustensils_node(state: RecipeAgentState) -> dict:
        plan = state["plan"]
        assert plan is not None
        logger.info(f"▶ [resolve_ustensils] {len(plan.ustensils)} ustensil(s)")
        t0 = time.perf_counter()
        resolved = {} if plan.components else await _resolve_ustensils_for_plan(plan, registry, matcher)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(f"◀ [resolve_ustensils] {len(resolved)} resolved in {elapsed_ms:.0f}ms")
        return {"resolved_ustensils": resolved}

    return resolve_ustensils_node


def make_create_recipe_node(registry: _MCPRecipeRegistry) -> Callable:
    async def create_recipe_node(state: RecipeAgentState) -> dict:
        plan = state["plan"]
        assert plan is not None
        logger.info(f"▶ [create_recipe] name={plan.name!r}")
        t0 = time.perf_counter()

        payload = _build_recipe_payload(
            plan,
            state["resolved_ingredients"],
            state["resolved_ustensils"],
            components=state["resolved_components"],
            include_ingredients=not bool(plan.components),
        )
        created = await registry.create_recipe(payload)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        logger.info(f"◀ [create_recipe] 🎉 uuid={created['uuid']} in {elapsed_ms:.0f}ms")
        content = _format_response(plan, created["uuid"], state["resolved_ingredients"], state["resolved_ustensils"])
        return {
            "recipe_uuid": created["uuid"],
            "messages": [{"role": "assistant", "content": content}],
        }

    return create_recipe_node


def make_link_ingredients_node(registry: _MCPRecipeRegistry) -> Callable:
    async def link_ingredients_node(state: RecipeAgentState) -> dict:
        logger.debug("[link_ingredients] skipped: recipe aggregate now carries ingredient references")
        return {}

    return link_ingredients_node


def make_link_ustensils_node(registry: _MCPRecipeRegistry) -> Callable:
    async def link_ustensils_node(state: RecipeAgentState) -> dict:
        logger.debug("[link_ustensils] skipped: recipe aggregate now carries equipment references")
        return {}

    return link_ustensils_node


def make_create_steps_node(registry: _MCPRecipeRegistry) -> Callable:
    async def create_steps_node(state: RecipeAgentState) -> dict:
        plan = state["plan"]
        assert plan is not None
        recipe_uuid = state["recipe_uuid"]
        assert recipe_uuid is not None
        logger.debug("[create_steps] skipped: recipe aggregate now carries steps")

        content = _format_response(plan, recipe_uuid, state["resolved_ingredients"], state["resolved_ustensils"])
        return {"messages": [{"role": "assistant", "content": content}]}

    return create_steps_node


_QUANTITY_WORDS = {
    "un": 1.0,
    "une": 1.0,
    "deux": 2.0,
    "trois": 3.0,
    "quatre": 4.0,
    "cinq": 5.0,
    "six": 6.0,
    "sept": 7.0,
    "huit": 8.0,
    "neuf": 9.0,
    "dix": 10.0,
}


def _parse_positive_float(value: str | None, default: float = 1.0) -> float:
    if value is None:
        return default
    raw = value.strip().lower().replace(",", ".")
    if not raw:
        return default
    fraction = re.search(r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)", raw)
    if fraction:
        numerator = float(fraction.group(1))
        denominator = float(fraction.group(2))
        if denominator:
            return max(numerator / denominator, 0.01)
    number = re.search(r"\d+(?:\.\d+)?", raw)
    if number:
        return max(float(number.group(0)), 0.01)
    for word, quantity in _QUANTITY_WORDS.items():
        if re.search(rf"\b{word}\b", raw):
            return quantity
    return default


def _parse_servings(value: str | None) -> int:
    return max(int(round(_parse_positive_float(value, default=1.0))), 1)


def _unit_from_quantity(quantity: str | None) -> str | None:
    if not quantity:
        return None
    raw = quantity.strip().lower().replace(",", ".")
    without_number = re.sub(r"^\s*(\d+(?:\.\d+)?\s*/\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?|\w+)\s*", "", raw)
    without_number = without_number.strip(" .-")
    return without_number or None


def _resolve_unit(quantity: str | None, unit: str | None) -> str:
    if unit and unit.strip():
        return unit.strip()
    inferred = _unit_from_quantity(quantity)
    if inferred:
        return inferred
    return "unité"


def _build_recipe_payload(
        plan: RecipePlanLike,
        resolved_ingredients: dict[str, str],
        resolved_ustensils: dict[str, str],
        components: list[dict] | None = None,
        include_ingredients: bool = True,
) -> dict:
    ingredients = []
    if include_ingredients:
        for line in plan.ingredients:
            ingredient_uuid = resolved_ingredients.get(line.name)
            if not ingredient_uuid:
                continue
            ingredients.append({
                "ingredient_uuid": ingredient_uuid,
                "quantity": _parse_positive_float(line.quantity),
                "unit": _resolve_unit(line.quantity, line.unit),
            })

    equipment = [
        {"equipment_uuid": equipment_uuid, "quantity": 1}
        for equipment_uuid in resolved_ustensils.values()
    ]

    steps = [
        {
            "name": step.title.strip(),
            "description": step.instruction.strip() if step.instruction else None,
            "preparation_time": step.duration_minutes,
            "rank": rank,
        }
        for rank, step in enumerate(plan.steps, 1)
        if step.title.strip()
    ]

    payload = {
        "name": plan.name,
        "description": plan.description,
        "servings": _parse_servings(plan.servings),
        "ingredients": ingredients,
        "equipment": equipment,
        "steps": steps,
    }
    if components:
        payload["components"] = components
    return payload


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
    if plan.components:
        lines.append("\n## 🧩 Sous-recettes")
        lines.extend(f"- {component.name}" for component in plan.components)
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
    ustensils = recipe.get("ustensils") or recipe.get("equipment") or []
    if ustensils:
        lines.append("\n## 🍳 Ustensiles")
        lines.extend(f"- {ust['name']}" for ust in ustensils)
    lines.extend(_format_existing_steps(recipe.get("steps") or []))
    return "\n".join(lines)


def _format_response_duplicate_confirmation(recipe: dict) -> str:
    return (
        f"ℹ️ **{recipe['name']}** existe déjà — 🆔 `{recipe['uuid']}`\n\n"
        "Aucune modification n'a été appliquée. Créer un doublon avec la recette structurée extraite ?"
    )
