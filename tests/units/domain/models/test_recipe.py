import pytest
from pydantic import ValidationError

from domain.models.recipe import (
    IngredientLine,
    RecipeComponentPlan,
    RecipePlan,
    RecipeResult,
    RecipeStep,
    UstensilLine,
)


def test_ingredient_line_minimal():
    ing = IngredientLine(name = "farine de blé")
    assert ing.name == "farine de blé"
    assert ing.unit is None
    assert ing.quantity is None


def test_ingredient_line_full():
    ing = IngredientLine(name = "sucre", unit = "g", quantity = "200")
    assert ing.unit == "g"
    assert ing.quantity == "200"


def test_ustensil_line():
    ust = UstensilLine(name = "fouet")
    assert ust.name == "fouet"


def test_recipe_step_minimal():
    step = RecipeStep(title = "Préparer", instruction = "Mélanger les ingrédients")
    assert step.title == "Préparer"
    assert step.instruction == "Mélanger les ingrédients"
    assert step.duration_minutes is None


def test_recipe_step_with_duration():
    step = RecipeStep(title = "Cuire", instruction = "Cuire 20 min au four", duration_minutes = 20)
    assert step.duration_minutes == 20


def test_recipe_plan_defaults():
    plan = RecipePlan(name = "Tarte Tatin")
    assert plan.name == "Tarte Tatin"
    assert plan.description is None
    assert plan.servings is None
    assert plan.prep_time_minutes is None
    assert plan.cook_time_minutes is None
    assert plan.ingredients == []
    assert plan.ustensils == []
    assert plan.steps == []
    assert plan.components == []


def test_recipe_plan_full():
    plan = RecipePlan(
        name = "Pizza Margherita",
        description = "Pizza classique italienne",
        servings = "4 personnes",
        prep_time_minutes = 30,
        cook_time_minutes = 20,
        ingredients = [
            IngredientLine(name = "farine", unit = "g", quantity = "500"),
            IngredientLine(name = "tomate"),
        ],
        ustensils = [UstensilLine(name = "four"), UstensilLine(name = "rouleau à pâtisserie")],
        steps = [
            RecipeStep(title = "Préparer la pâte", instruction = "Pétrir la farine", duration_minutes = 15),
            RecipeStep(title = "Cuire", instruction = "Mettre au four"),
        ],
    )
    assert len(plan.ingredients) == 2
    assert len(plan.ustensils) == 2
    assert len(plan.steps) == 2
    assert plan.prep_time_minutes == 30
    assert plan.cook_time_minutes == 20


def test_recipe_plan_with_component():
    plan = RecipePlan(
        name = "Île flottante",
        components = [
            RecipeComponentPlan(
                name = "Crème anglaise",
                ingredients = [IngredientLine(name = "lait", unit = "ml", quantity = "500")],
                steps = [RecipeStep(title = "Cuire", instruction = "Cuire la crème")],
            )
        ],
    )

    assert len(plan.components) == 1
    assert plan.components[0].name == "Crème anglaise"
    assert plan.components[0].servings_multiplier == 1.0


def test_recipe_result():
    result = RecipeResult(
        recipe_uuid = "uuid-recipe",
        recipe_name = "Tarte Tatin",
        resolved_ingredients = {"pomme": "uuid-ing-1", "beurre": "uuid-ing-2"},
        resolved_ustensils = {"moule": "uuid-ust-1"},
        formatted_response = "✅ Tarte Tatin créée avec succès",
    )
    assert result.recipe_uuid == "uuid-recipe"
    assert result.recipe_name == "Tarte Tatin"
    assert result.resolved_ingredients["pomme"] == "uuid-ing-1"
    assert result.resolved_ustensils["moule"] == "uuid-ust-1"
    assert "Tarte Tatin" in result.formatted_response


def test_recipe_result_empty_maps():
    result = RecipeResult(
        recipe_uuid = "uuid-1",
        recipe_name = "Soupe",
        resolved_ingredients = {},
        resolved_ustensils = {},
        formatted_response = "✅ Soupe",
    )
    assert result.resolved_ingredients == {}
    assert result.resolved_ustensils == {}


def test_ingredient_line_requires_name():
    with pytest.raises(ValidationError):
        IngredientLine()  # type: ignore[call-arg]
