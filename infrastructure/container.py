from adapters.output.mongodb.agent_run_repository import MongoDBAgentRunRepository
from adapters.output.recipe_agent.agent_adapter import RecipeAgentAdapter
from application.services.agent_run_service import AgentRunService
from application.services.recipe_service import RecipeService
from application.use_cases.process_raw_recipe import ProcessRawRecipeUseCase
from arclith import Arclith, Logger
from arclith.adapters.output.mongodb.config import MongoDBConfig
from infrastructure.config import AgentConfig


def build_container(
        arclith: Arclith, agent_config: AgentConfig
) -> tuple[RecipeService, AgentRunService, Logger]:
    mongo = arclith.config.adapters.mongodb
    if mongo is None:
        raise RuntimeError("MongoDB settings required (adapters.mongodb in config.yaml)")

    run_repository = MongoDBAgentRunRepository(
        MongoDBConfig(uri = mongo.uri, db_name = mongo.db_name, collection_name = "agent_runs"),
        arclith.logger,
    )

    agent = RecipeAgentAdapter(agent_config)
    use_case = ProcessRawRecipeUseCase(agent, run_repository, arclith.logger)
    recipe_service = RecipeService(use_case)
    run_service = AgentRunService(run_repository, arclith.logger)

    return recipe_service, run_service, arclith.logger
