import time

from arclith.domain.ports.logger import Logger
from arclith.domain.ports.repository import Repository

from domain.models.agent_run import AgentRun
from domain.models.recipe import RecipeResult
from domain.ports.recipe_agent import RecipeAgentPort


class ProcessRawRecipeUseCase:
    def __init__(
            self,
            agent: RecipeAgentPort,
            run_repository: Repository[AgentRun],
            logger: Logger,
    ) -> None:
        self._agent = agent
        self._run_repository = run_repository
        self._logger = logger

    async def execute(self, raw_text: str) -> RecipeResult:
        run = await self._run_repository.create(AgentRun(raw_input = raw_text, status = "running"))
        run_uuid = str(run.uuid)
        self._logger.info("▶ Agent run started", run_uuid = run_uuid, input_length = len(raw_text))
        t0 = time.perf_counter()

        try:
            result = await self._agent.process(raw_text, run_uuid)
            elapsed_ms = round((time.perf_counter() - t0) * 1000)
            await self._run_repository.update(
                run.model_copy(update = {
                    "status": "success",
                    "recipe_uuid": result.recipe_uuid,
                    "recipe_name": result.recipe_name,
                    "metadata": {
                        "elapsed_ms": elapsed_ms,
                        "resolved_ingredients": len(result.resolved_ingredients),
                        "resolved_ustensils": len(result.resolved_ustensils),
                    },
                })
            )
            self._logger.info(
                "◀ Agent run succeeded",
                run_uuid = run_uuid,
                recipe_uuid = result.recipe_uuid,
                elapsed_ms = elapsed_ms,
            )
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - t0) * 1000)
            await self._run_repository.update(
                run.model_copy(update = {
                    "status": "failed",
                    "error": str(exc),
                    "metadata": {"elapsed_ms": elapsed_ms},
                })
            )
            self._logger.error("💥 Agent run failed", run_uuid = run_uuid, error = str(exc))
            raise

        return result
