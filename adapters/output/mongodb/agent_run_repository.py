from arclith.adapters.output.mongodb.config import MongoDBConfig
from arclith.adapters.output.mongodb.repository import MongoDBRepository
from arclith.domain.ports.logger import Logger

from domain.models.agent_run import AgentRun


class MongoDBAgentRunRepository(MongoDBRepository[AgentRun]):
    def __init__(self, config: MongoDBConfig, logger: Logger) -> None:
        super().__init__(config, AgentRun, logger)
