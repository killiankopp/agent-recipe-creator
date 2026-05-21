import asyncio
from pathlib import Path

import typer
from arclith import Arclith
from infrastructure.config import load_agent_config
from infrastructure.container import build_container

app = typer.Typer(name = "recipe-agent", help = "Agent de création de recettes par IA")

_CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config.yaml"


@app.command()
def create(
        raw_text: str = typer.Argument(..., help = "Texte brut de la recette (guillemets si espaces)"),
        config: Path = typer.Option(_CONFIG_PATH, "--config", "-c", help = "Chemin vers config.yaml"),
        allow_duplicate: bool = typer.Option(
            False,
            "--allow-duplicate",
            help = "Créer un doublon si une recette équivalente existe déjà.",
        ),
) -> None:
    """Structure and register a raw recipe via AI agent."""
    asyncio.run(_run_create(raw_text, config, allow_duplicate = allow_duplicate))


async def _run_create(raw_text: str, config_path: Path, *, allow_duplicate: bool = False) -> None:
    arclith = Arclith(config_path)
    agent_config = load_agent_config(config_path)
    recipe_service, _, logger = build_container(arclith, agent_config)

    try:
        result = await recipe_service.ai_create(raw_text, allow_duplicate = allow_duplicate)
        typer.echo(result.formatted_response)
        typer.echo(f"\n🆔 recipe_uuid={result.recipe_uuid}")
    except Exception as exc:
        typer.echo(f"❌ Erreur : {exc}", err = True)
        raise typer.Exit(code = 1) from exc
