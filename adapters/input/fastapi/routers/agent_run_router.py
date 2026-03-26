from fastapi import APIRouter, HTTPException
from uuid import UUID as StdUUID
from uuid6 import UUID

from adapters.input.schemas.agent_run_schema import AgentRunSchema
from application.services.agent_run_service import AgentRunService
from arclith.adapters.input.schemas import ApiResponse, success_response
from arclith.domain.ports.logger import Logger


class AgentRunRouter:
    def __init__(self, service: AgentRunService, logger: Logger) -> None:
        self._service = service
        self._logger = logger
        self.router = APIRouter(prefix = "/v1/agent-runs", tags = ["agent-runs"])
        self._register_routes()

    def _register_routes(self) -> None:
        self.router.add_api_route(
            methods = ["GET"],
            path = "/",
            endpoint = self.list_runs,
            summary = "List agent runs",
            response_model = ApiResponse[list[AgentRunSchema]],
            response_description = "List of all agent runs",
        )
        self.router.add_api_route(
            methods = ["GET"],
            path = "/{uuid}",
            endpoint = self.get_run,
            summary = "Get agent run",
            response_model = ApiResponse[AgentRunSchema],
            response_description = "The agent run",
            responses = {404: {"description": "Agent run not found"}},
        )

    async def list_runs(self) -> ApiResponse[list[AgentRunSchema]]:
        """List all agent runs."""
        runs = await self._service.find_all()
        data = [AgentRunSchema.model_validate(r, from_attributes = True) for r in runs]
        return success_response(data = data, links = {"self": "/v1/agent-runs"})

    async def get_run(self, uuid: StdUUID) -> ApiResponse[AgentRunSchema]:
        """Get a specific agent run by UUID."""
        run = await self._service.read(UUID(str(uuid)))
        if run is None:
            raise HTTPException(status_code = 404, detail = "Agent run not found")
        return success_response(
            data = AgentRunSchema.model_validate(run, from_attributes = True),
            links = {"self": f"/v1/agent-runs/{uuid}", "collection": "/v1/agent-runs"},
        )
