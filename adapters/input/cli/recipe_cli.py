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
) -> None:
    """Structure and register a raw recipe via AI agent."""
    asyncio.run(_run_create(raw_text, config))


async def _run_create(raw_text: str, config_path: Path) -> None:
    arclith = Arclith(config_path)
    agent_config = load_agent_config(config_path)
    recipe_service, _, logger = build_container(arclith, agent_config)

    try:
        result = await recipe_service.ai_create(raw_text)
        typer.echo(result.formatted_response)
        typer.echo(f"\n🆔 recipe_uuid={result.recipe_uuid}")
    except Exception as exc:
        typer.echo(f"❌ Erreur : {exc}", err = True)
        raise typer.Exit(code = 1) from exc
