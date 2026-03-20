from fastapi import FastAPI

from arclith import Arclith
from adapters.input.fastapi.ingredient_router import IngredientRouter
from infrastructure.ingredient_container import build_ingredient_service


def register_routers(app: FastAPI, arclith: Arclith) -> None:
    service, logger = build_ingredient_service(arclith)
    app.include_router(IngredientRouter(service, logger).router)
