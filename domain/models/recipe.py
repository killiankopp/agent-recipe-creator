from pydantic import BaseModel, Field


class IngredientLine(BaseModel):
    name: str = Field(description = "Nom de l'ingrédient (ex. Farine de blé)")
    unit: str | None = Field(default = None, description = "Unité de mesure (g, kg, ml, …). None si non applicable.")
    quantity: str | None = Field(default = None,
                                 description = "Quantité (ex. 180, 3-4, une pincée). None si non précisée.")


class UstensilLine(BaseModel):
    name: str = Field(description = "Nom de l'ustensile (ex. Fouet, Poêle)")


class RecipeStep(BaseModel):
    title: str = Field(description = "Titre court de l'étape (ex. Sabler la pâte)")
    instruction: str = Field(description = "Description complète de l'étape")
    duration_minutes: int | None = Field(default = None,
                                         description = "Durée estimée en minutes. None si non précisée.")


class RecipeComponentPlan(BaseModel):
    name: str = Field(description = "Nom de la sous-recette (ex. Meringue, Caramel, Crème anglaise)")
    description: str | None = Field(default = None, description = "Description courte de la sous-recette")
    servings: str | None = Field(default = None, description = "Nombre de portions de la sous-recette")
    prep_time_minutes: int | None = Field(default = None, description = "Temps de préparation en minutes")
    cook_time_minutes: int | None = Field(default = None, description = "Temps de cuisson en minutes")
    ingredients: list[IngredientLine] = Field(default_factory = list)
    ustensils: list[UstensilLine] = Field(default_factory = list)
    steps: list[RecipeStep] = Field(default_factory = list)
    servings_multiplier: float = Field(default = 1.0, gt = 0)


class RecipePlan(BaseModel):
    name: str = Field(description = "Nom de la recette")
    description: str | None = Field(default = None, description = "Description courte de la recette")
    servings: str | None = Field(default = None, description = "Nombre de portions (ex. 60 biscuits, 4 personnes)")
    prep_time_minutes: int | None = Field(default = None, description = "Temps de préparation en minutes")
    cook_time_minutes: int | None = Field(default = None, description = "Temps de cuisson en minutes")
    ingredients: list[IngredientLine] = Field(default_factory = list)
    ustensils: list[UstensilLine] = Field(default_factory = list)
    steps: list[RecipeStep] = Field(default_factory = list)
    components: list[RecipeComponentPlan] = Field(default_factory = list)


class RecipeResult(BaseModel):
    recipe_uuid: str
    recipe_name: str
    resolved_ingredients: dict[str, str]  # name → uuid
    resolved_ustensils: dict[str, str]  # name → uuid
    formatted_response: str
    created: bool = True
    duplicate_confirmation_required: bool = False
    existing_recipe_uuid: str | None = None
    existing_recipe_name: str | None = None
