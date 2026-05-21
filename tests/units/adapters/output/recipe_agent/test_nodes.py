from langchain_core.messages import HumanMessage

from adapters.output.recipe_agent._nodes import (
    _format_response,
    _format_response_existing,
    make_check_recipe_node,
    make_create_components_node,
    make_create_recipe_node,
    make_create_steps_node,
    make_link_ingredients_node,
    make_link_ustensils_node,
    make_plan_node,
    make_review_plan_node,
    make_resolve_ingredients_node,
    make_resolve_ustensils_node,
)
from domain.models.recipe import IngredientLine, RecipeComponentPlan, RecipePlan, RecipeStep, UstensilLine


# ── Fakes ─────────────────────────────────────────────────────────────────────


class FakePlanner:
    def __init__(self, plan: RecipePlan) -> None:
        self._plan = plan

    async def plan(self, user_input: str) -> RecipePlan:
        return self._plan

    async def review(self, raw_text: str, plan: RecipePlan) -> RecipePlan:
        return plan


class FakeRegistry:
    def __init__(self) -> None:
        self.created_ingredients: list[dict] = []
        self.created_ustensils: list[dict] = []
        self.created_recipes: list[dict] = []
        self.created_steps: list[dict] = []
        self.linked_ingredients: list[tuple] = []
        self.linked_ustensils: list[tuple] = []

    async def list_ingredients(self, name: str) -> list[dict]:
        return []

    async def create_ingredient(self, name: str, unit: str | None) -> dict:
        item = {"uuid": f"ing-{name}", "name": name, "unit": unit}
        self.created_ingredients.append(item)
        return item

    async def list_equipment(self, name: str) -> list[dict]:
        return []

    async def create_equipment(self, name: str) -> dict:
        item = {"uuid": f"ust-{name}", "name": name}
        self.created_ustensils.append(item)
        return item

    async def list_recipes(self, name: str) -> list[dict]:
        return []

    async def create_recipe(self, payload: dict) -> dict:
        item = {"uuid": "recipe-uuid", **payload}
        self.created_recipes.append(item)
        return item

    async def link_ingredient_to_recipe(self, recipe_uuid: str, ingredient_uuid: str) -> dict:
        self.linked_ingredients.append((recipe_uuid, ingredient_uuid))
        return {"recipe_uuid": recipe_uuid, "ingredient_uuid": ingredient_uuid}

    async def link_ustensil_to_recipe(self, recipe_uuid: str, ustensil_uuid: str) -> dict:
        self.linked_ustensils.append((recipe_uuid, ustensil_uuid))
        return {"recipe_uuid": recipe_uuid, "ustensil_uuid": ustensil_uuid}

    async def create_step(self, recipe_uuid: str, name: str, description: str | None) -> dict:
        item = {"uuid": f"step-{name}", "recipe_uuid": recipe_uuid, "name": name}
        self.created_steps.append(item)
        return item


class FakeRegistryWithExistingIngredient(FakeRegistry):
    async def list_ingredients(self, name: str) -> list[dict]:
        return [{"uuid": "existing-ing", "name": name}]


class FakeRegistryWithExistingUstensil(FakeRegistry):
    async def list_equipment(self, name: str) -> list[dict]:
        return [{"uuid": "existing-ust", "name": name}]


class FakeRegistryWithExistingRecipe(FakeRegistry):
    async def list_recipes(self, name: str) -> list[dict]:
        return [{"uuid": "existing-recipe", "name": name}]


class FakeRegistryWithLinkError(FakeRegistry):
    async def link_ingredient_to_recipe(self, recipe_uuid: str, ingredient_uuid: str) -> dict:
        return {"error": "already linked"}

    async def link_ustensil_to_recipe(self, recipe_uuid: str, ustensil_uuid: str) -> dict:
        return {"error": "already linked"}


def _no_match(name: str, candidates: list[dict]) -> dict | None:
    return None


def _always_match(name: str, candidates: list[dict]) -> dict | None:
    return candidates[0] if candidates else None


def _base_state(**kwargs) -> dict:
    return {
        "messages": [],
        "plan": None,
        "resolved_ingredients": {},
        "resolved_ustensils": {},
        "resolved_components": [],
        "recipe_uuid": None,
        "recipe_exists": None,
        "allow_duplicate": False,
        "existing_recipe_uuid": None,
        "existing_recipe_name": None,
        "error": None,
        **kwargs,
    }


def _make_plan(**kwargs) -> RecipePlan:
    defaults = dict(name = "Beignets", description = "Beignets moelleux")
    return RecipePlan(**(defaults | kwargs))


# ── plan node ─────────────────────────────────────────────────────────────────


async def test_plan_node_returns_plan():
    expected = _make_plan()
    node = make_plan_node(FakePlanner(expected))
    state = _base_state(messages = [HumanMessage(content = "recette de beignets")])
    result = await node(state)
    assert result["plan"] is expected


async def test_plan_node_passes_message_content():
    received: list[str] = []

    class _CapturingPlanner:
        async def plan(self, user_input: str) -> RecipePlan:
            received.append(user_input)
            return _make_plan()

    node = make_plan_node(_CapturingPlanner())
    state = _base_state(messages = [HumanMessage(content = "ma recette spéciale")])
    await node(state)
    assert received == ["ma recette spéciale"]


async def test_review_plan_node_returns_reviewed_plan():
    initial = _make_plan(name = "Beignets")
    reviewed = _make_plan(name = "Beignets validés", ingredients = [IngredientLine(name = "sucre")])

    class _ReviewingPlanner:
        async def review(self, raw_text: str, plan: RecipePlan) -> RecipePlan:
            assert raw_text == "recette brute"
            assert plan is initial
            return reviewed

    node = make_review_plan_node(_ReviewingPlanner())
    state = _base_state(plan = initial, messages = [HumanMessage(content = "recette brute")])
    result = await node(state)

    assert result["plan"] is reviewed


# ── check_recipe node ──────────────────────────────────────────────────────────


async def test_check_recipe_not_found():
    registry = FakeRegistry()
    node = make_check_recipe_node(registry, _no_match)
    state = _base_state(plan = _make_plan())
    result = await node(state)
    assert result["recipe_exists"] is False


async def test_check_recipe_found():
    registry = FakeRegistryWithExistingRecipe()
    node = make_check_recipe_node(registry, _always_match)
    state = _base_state(plan = _make_plan(name = "Beignets"))
    result = await node(state)
    assert result["recipe_exists"] is True
    assert result["recipe_uuid"] == "existing-recipe"
    assert len(result["messages"]) == 1
    assert "Beignets" in result["messages"][0]["content"]


async def test_check_recipe_found_with_duplicate_allowed_continues_to_create():
    registry = FakeRegistryWithExistingRecipe()
    node = make_check_recipe_node(registry, _always_match)
    state = _base_state(plan = _make_plan(name = "Beignets"), allow_duplicate = True)
    result = await node(state)
    assert result["recipe_exists"] is False
    assert result["existing_recipe_uuid"] == "existing-recipe"
    assert result["existing_recipe_name"] == "Beignets"
    assert "messages" not in result


# ── resolve_ingredients node ───────────────────────────────────────────────────


async def test_resolve_ingredients_creates_when_not_found():
    registry = FakeRegistry()
    node = make_resolve_ingredients_node(registry, _no_match)
    plan = _make_plan(ingredients = [IngredientLine(name = "farine", unit = "g", quantity = "200")])
    state = _base_state(plan = plan)
    result = await node(state)
    assert "farine" in result["resolved_ingredients"]
    assert result["resolved_ingredients"]["farine"] == "ing-farine"
    assert len(registry.created_ingredients) == 1


async def test_resolve_ingredients_reuses_existing():
    registry = FakeRegistryWithExistingIngredient()
    node = make_resolve_ingredients_node(registry, _always_match)
    plan = _make_plan(ingredients = [IngredientLine(name = "farine")])
    state = _base_state(plan = plan)
    result = await node(state)
    assert result["resolved_ingredients"]["farine"] == "existing-ing"
    assert len(registry.created_ingredients) == 0


async def test_resolve_ingredients_multiple():
    registry = FakeRegistry()
    node = make_resolve_ingredients_node(registry, _no_match)
    plan = _make_plan(
        ingredients = [
            IngredientLine(name = "farine"),
            IngredientLine(name = "sucre"),
            IngredientLine(name = "oeuf"),
        ]
    )
    state = _base_state(plan = plan)
    result = await node(state)
    assert len(result["resolved_ingredients"]) == 3
    assert len(registry.created_ingredients) == 3


async def test_resolve_ingredients_empty_plan():
    registry = FakeRegistry()
    node = make_resolve_ingredients_node(registry, _no_match)
    state = _base_state(plan = _make_plan(ingredients = []))
    result = await node(state)
    assert result["resolved_ingredients"] == {}


async def test_resolve_ingredients_skips_parent_total_when_components_exist():
    registry = FakeRegistry()
    node = make_resolve_ingredients_node(registry, _no_match)
    state = _base_state(
        plan = _make_plan(
            ingredients = [IngredientLine(name = "lait")],
            components = [RecipeComponentPlan(name = "Crème anglaise")],
        )
    )
    result = await node(state)
    assert result["resolved_ingredients"] == {}
    assert registry.created_ingredients == []


# ── create_components node ─────────────────────────────────────────────────────


async def test_create_components_creates_missing_child_recipe():
    registry = FakeRegistry()
    node = make_create_components_node(registry, _no_match)
    plan = _make_plan(
        components = [
            RecipeComponentPlan(
                name = "Crème anglaise",
                ingredients = [IngredientLine(name = "lait", quantity = "500", unit = "ml")],
                steps = [RecipeStep(title = "Cuire", instruction = "Cuire la crème")],
            )
        ]
    )
    result = await node(_base_state(plan = plan))

    assert result["resolved_components"][0]["recipe_uuid"] == "recipe-uuid"
    assert result["resolved_components"][0]["label"] == "Crème anglaise"
    assert registry.created_recipes[0]["name"] == "Crème anglaise"
    assert registry.created_recipes[0]["ingredients"][0]["unit"] == "ml"


async def test_create_components_reuses_existing_child_recipe():
    registry = FakeRegistryWithExistingRecipe()
    node = make_create_components_node(registry, _always_match)
    plan = _make_plan(components = [RecipeComponentPlan(name = "Meringue")])
    result = await node(_base_state(plan = plan))

    assert result["resolved_components"] == [{
        "recipe_uuid": "existing-recipe",
        "label": "Meringue",
        "rank": 1,
        "servings_multiplier": 1.0,
    }]
    assert registry.created_recipes == []


# ── resolve_ustensils node ─────────────────────────────────────────────────────


async def test_resolve_ustensils_creates_when_not_found():
    registry = FakeRegistry()
    node = make_resolve_ustensils_node(registry, _no_match)
    plan = _make_plan(ustensils = [UstensilLine(name = "fouet")])
    state = _base_state(plan = plan)
    result = await node(state)
    assert "fouet" in result["resolved_ustensils"]
    assert result["resolved_ustensils"]["fouet"] == "ust-fouet"
    assert len(registry.created_ustensils) == 1


async def test_resolve_ustensils_reuses_existing():
    registry = FakeRegistryWithExistingUstensil()
    node = make_resolve_ustensils_node(registry, _always_match)
    plan = _make_plan(ustensils = [UstensilLine(name = "fouet")])
    state = _base_state(plan = plan)
    result = await node(state)
    assert result["resolved_ustensils"]["fouet"] == "existing-ust"
    assert len(registry.created_ustensils) == 0


async def test_resolve_ustensils_empty_plan():
    registry = FakeRegistry()
    node = make_resolve_ustensils_node(registry, _no_match)
    state = _base_state(plan = _make_plan(ustensils = []))
    result = await node(state)
    assert result["resolved_ustensils"] == {}


# ── create_recipe node ─────────────────────────────────────────────────────────


async def test_create_recipe_stores_uuid():
    registry = FakeRegistry()
    node = make_create_recipe_node(registry)
    state = _base_state(plan = _make_plan(name = "Tarte Tatin", description = "Tarte aux pommes caramélisées"))
    result = await node(state)
    assert result["recipe_uuid"] == "recipe-uuid"
    assert len(registry.created_recipes) == 1
    assert registry.created_recipes[0]["name"] == "Tarte Tatin"
    assert registry.created_recipes[0]["servings"] == 1
    assert registry.created_recipes[0]["ingredients"] == []


async def test_create_recipe_includes_resolved_components():
    registry = FakeRegistry()
    node = make_create_recipe_node(registry)
    plan = _make_plan(
        name = "Île flottante",
        ingredients = [IngredientLine(name = "lait")],
        components = [RecipeComponentPlan(name = "Crème anglaise")],
    )
    state = _base_state(
        plan = plan,
        resolved_components = [{"recipe_uuid": "child-1", "label": "Crème anglaise", "rank": 1, "servings_multiplier": 1}],
    )
    await node(state)

    assert registry.created_recipes[0]["components"][0]["recipe_uuid"] == "child-1"
    assert registry.created_recipes[0]["ingredients"] == []


async def test_create_recipe_without_description():
    registry = FakeRegistry()
    node = make_create_recipe_node(registry)
    state = _base_state(plan = _make_plan(name = "Soupe", description = None))
    result = await node(state)
    assert result["recipe_uuid"] == "recipe-uuid"


# ── link_ingredients node ──────────────────────────────────────────────────────


async def test_link_ingredients_links_all():
    registry = FakeRegistry()
    node = make_link_ingredients_node(registry)
    state = _base_state(
        recipe_uuid = "r-1",
        resolved_ingredients = {"farine": "i-1", "sucre": "i-2"},
    )
    result = await node(state)
    assert result == {}
    assert registry.linked_ingredients == []


async def test_link_ingredients_tolerates_error_response():
    registry = FakeRegistryWithLinkError()
    node = make_link_ingredients_node(registry)
    state = _base_state(recipe_uuid = "r-1", resolved_ingredients = {"farine": "i-1"})
    result = await node(state)
    assert result == {}


async def test_link_ingredients_empty():
    registry = FakeRegistry()
    node = make_link_ingredients_node(registry)
    state = _base_state(recipe_uuid = "r-1", resolved_ingredients = {})
    result = await node(state)
    assert result == {}
    assert len(registry.linked_ingredients) == 0


# ── link_ustensils node ────────────────────────────────────────────────────────


async def test_link_ustensils_links_all():
    registry = FakeRegistry()
    node = make_link_ustensils_node(registry)
    state = _base_state(recipe_uuid = "r-1", resolved_ustensils = {"fouet": "u-1"})
    result = await node(state)
    assert result == {}
    assert registry.linked_ustensils == []


async def test_link_ustensils_tolerates_error_response():
    registry = FakeRegistryWithLinkError()
    node = make_link_ustensils_node(registry)
    state = _base_state(recipe_uuid = "r-1", resolved_ustensils = {"fouet": "u-1"})
    result = await node(state)
    assert result == {}


# ── create_steps node ──────────────────────────────────────────────────────────


async def test_create_steps_creates_all():
    registry = FakeRegistry()
    node = make_create_steps_node(registry)
    plan = _make_plan(
        steps = [
            RecipeStep(title = "Préparer", instruction = "Mélanger les ingrédients"),
            RecipeStep(title = "Cuire", instruction = "Mettre au four 20 min"),
        ]
    )
    state = _base_state(
        plan = plan,
        recipe_uuid = "r-1",
        resolved_ingredients = {},
        resolved_ustensils = {},
    )
    result = await node(state)
    assert registry.created_steps == []
    assert "messages" in result
    assert len(result["messages"]) == 1


async def test_create_steps_formatted_response_contains_recipe_name():
    registry = FakeRegistry()
    node = make_create_steps_node(registry)
    plan = _make_plan(
        name = "Tarte Tatin",
        steps = [RecipeStep(title = "Caraméliser", instruction = "Faire fondre le sucre")],
    )
    state = _base_state(
        plan = plan, recipe_uuid = "r-1", resolved_ingredients = {}, resolved_ustensils = {}
    )
    result = await node(state)
    content = result["messages"][0]["content"]
    assert "Tarte Tatin" in content
    assert "r-1" in content


async def test_create_steps_no_steps():
    registry = FakeRegistry()
    node = make_create_steps_node(registry)
    state = _base_state(
        plan = _make_plan(steps = []),
        recipe_uuid = "r-1",
        resolved_ingredients = {},
        resolved_ustensils = {},
    )
    result = await node(state)
    assert len(registry.created_steps) == 0
    assert "messages" in result


# ── _format_response ───────────────────────────────────────────────────────────


def test_format_response_minimal():
    plan = RecipePlan(name = "Soupe")
    text = _format_response(plan, "uuid-1", {}, {})
    assert "Soupe" in text
    assert "uuid-1" in text


def test_format_response_with_description():
    plan = RecipePlan(name = "Soupe", description = "Soupe de légumes")
    text = _format_response(plan, "uuid-1", {}, {})
    assert "Soupe de légumes" in text


def test_format_response_meta_fields():
    plan = RecipePlan(name = "Pizza", servings = "4 personnes", prep_time_minutes = 20, cook_time_minutes = 15)
    text = _format_response(plan, "uuid-1", {}, {})
    assert "4 personnes" in text
    assert "20" in text
    assert "15" in text


def test_format_response_with_ingredients():
    plan = RecipePlan(
        name = "Gâteau",
        ingredients = [
            IngredientLine(name = "farine", unit = "g", quantity = "200"),
            IngredientLine(name = "sucre"),
        ],
    )
    text = _format_response(plan, "uuid-1", {}, {})
    assert "farine" in text
    assert "sucre" in text
    assert "200" in text
    assert "g" in text


def test_format_response_with_ustensils():
    plan = RecipePlan(name = "Omelette", ustensils = [UstensilLine(name = "poêle")])
    text = _format_response(plan, "uuid-1", {}, {})
    assert "poêle" in text


def test_format_response_with_steps():
    plan = RecipePlan(
        name = "Crêpes",
        steps = [
            RecipeStep(title = "Préparer", instruction = "Mélanger", duration_minutes = 5),
            RecipeStep(title = "Cuire", instruction = "Faire cuire"),
        ],
    )
    text = _format_response(plan, "uuid-1", {}, {})
    assert "Préparer" in text
    assert "Cuire" in text
    assert "Mélanger" in text
    assert "5" in text


# ── _format_response_existing ──────────────────────────────────────────────────


def test_format_response_existing_minimal():
    recipe = {"uuid": "r-1", "name": "Tarte Tatin"}
    text = _format_response_existing(recipe)
    assert "Tarte Tatin" in text
    assert "r-1" in text


def test_format_response_existing_with_description():
    recipe = {"uuid": "r-1", "name": "Soupe", "description": "Soupe chaude"}
    text = _format_response_existing(recipe)
    assert "Soupe chaude" in text


def test_format_response_existing_with_nutriscore():
    recipe = {"uuid": "r-1", "name": "Salade", "nutriscore": "A"}
    text = _format_response_existing(recipe)
    assert "A" in text


def test_format_response_existing_with_ingredients():
    recipe = {
        "uuid": "r-1",
        "name": "Pizza",
        "ingredients": [
            {"name": "tomate", "unit": "g"},
            {"name": "mozzarella"},
        ],
    }
    text = _format_response_existing(recipe)
    assert "tomate" in text
    assert "mozzarella" in text
    assert "(g)" in text


def test_format_response_existing_with_ustensils():
    recipe = {
        "uuid": "r-1",
        "name": "Gâteau",
        "ustensils": [{"name": "moule"}, {"name": "fouet"}],
    }
    text = _format_response_existing(recipe)
    assert "moule" in text
    assert "fouet" in text


def test_format_response_existing_with_steps():
    recipe = {
        "uuid": "r-1",
        "name": "Soufflé",
        "steps": [
            {"name": "Préparer", "description": "Mélanger"},
            {"name": "Cuire"},
        ],
    }
    text = _format_response_existing(recipe)
    assert "Préparer" in text
    assert "Mélanger" in text
    assert "Cuire" in text
