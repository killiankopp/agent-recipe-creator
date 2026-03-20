from arclith import BaseService, Logger
from arclith.domain.ports.repository import Repository

from domain.models.agent_run import AgentRun


class AgentRunService(BaseService[AgentRun]):
    def __init__(self, repository: Repository[AgentRun], logger: Logger) -> None:
        super().__init__(repository, logger)
