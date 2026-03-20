from uuid import UUID as StdUUID

from adapters.input.schemas.agent_run_schema import AgentRunSchema
from application.services.agent_run_service import AgentRunService
from arclith.domain.ports.logger import Logger
from fastapi import APIRouter, HTTPException
from uuid6 import UUID


class AgentRunRouter:
    def __init__(self, service: AgentRunService, logger: Logger) -> None:
        self._service = service
        self._logger = logger
        self.router = APIRouter(prefix = "/v1/agent-runs", tags = ["agent-runs"])
        self._register_routes()

    def _register_routes(self) -> None:
        self.router.add_api_route("/", self.list_runs, methods = ["GET"], response_model = list[AgentRunSchema])
        self.router.add_api_route("/{uuid}", self.get_run, methods = ["GET"], response_model = AgentRunSchema)

    async def list_runs(self) -> list[AgentRunSchema]:
        """List all agent runs."""
        runs = await self._service.find_all()
        return [AgentRunSchema.model_validate(r, from_attributes = True) for r in runs]

    async def get_run(self, uuid: StdUUID) -> AgentRunSchema:
        """Get a specific agent run by UUID."""
        run = await self._service.read(UUID(str(uuid)))
        if run is None:
            raise HTTPException(status_code = 404, detail = "Agent run not found")
        return AgentRunSchema.model_validate(run, from_attributes = True)
