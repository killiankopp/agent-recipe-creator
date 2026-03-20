from pathlib import Path

from arclith import Arclith
from adapters.input.fastapi.router import register_routers

arclith = Arclith(Path(__file__).parent / "config.yaml")
app = arclith.fastapi()
register_routers(app, arclith)

if __name__ == "__main__":
    arclith.run_api("main_api:app")
