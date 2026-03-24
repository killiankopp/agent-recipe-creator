from unittest.mock import MagicMock, patch

import pytest

from infrastructure.container import build_container


def _mock_arclith(mongo=True):
    arclith = MagicMock()
    arclith.logger = MagicMock()
    if mongo:
        arclith.config.adapters.mongodb.uri = "mongodb://localhost:27017"
        arclith.config.adapters.mongodb.db_name = "test"
    else:
        arclith.config.adapters.mongodb = None
    return arclith


def test_build_container_raises_without_mongodb():
    with pytest.raises(RuntimeError, match="MongoDB settings required"):
        build_container(_mock_arclith(mongo=False), MagicMock())


def test_build_container_returns_services():
    from application.services.recipe_service import RecipeService
    from application.services.agent_run_service import AgentRunService

    with (
        patch("infrastructure.container.MongoDBAgentRunRepository"),
        patch("infrastructure.container.RecipeAgentAdapter"),
    ):
        recipe_service, run_service, logger = build_container(
            _mock_arclith(), MagicMock()
        )

    assert isinstance(recipe_service, RecipeService)
    assert isinstance(run_service, AgentRunService)

