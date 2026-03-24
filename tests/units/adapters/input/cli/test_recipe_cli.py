from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from adapters.input.cli.recipe_cli import _run_create, app
from domain.models.recipe import RecipeResult

_RESULT = RecipeResult(
    recipe_uuid="r-uuid",
    recipe_name="Carbonara",
    resolved_ingredients={},
    resolved_ustensils={},
    formatted_response="✅ Carbonara créée",
)


async def test_run_create_success(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("")
    with (
        patch("adapters.input.cli.recipe_cli.Arclith"),
        patch("adapters.input.cli.recipe_cli.load_agent_config"),
        patch("adapters.input.cli.recipe_cli.build_container") as mock_bc,
    ):
        service = MagicMock()
        service.ai_create = AsyncMock(return_value=_RESULT)
        mock_bc.return_value = (service, MagicMock(), MagicMock())
        await _run_create("pasta carbonara", config)
        service.ai_create.assert_awaited_once_with("pasta carbonara")


async def test_run_create_raises_on_error(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("")
    with (
        patch("adapters.input.cli.recipe_cli.Arclith"),
        patch("adapters.input.cli.recipe_cli.load_agent_config"),
        patch("adapters.input.cli.recipe_cli.build_container") as mock_bc,
    ):
        service = MagicMock()
        service.ai_create = AsyncMock(side_effect=RuntimeError("boom"))
        mock_bc.return_value = (service, MagicMock(), MagicMock())
        with pytest.raises(typer.Exit):
            await _run_create("bad input", config)

