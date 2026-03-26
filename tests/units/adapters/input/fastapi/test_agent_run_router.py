import pytest
import uuid as _uuid
from fastapi import HTTPException

from adapters.input.fastapi.routers.agent_run_router import AgentRunRouter
from application.services.agent_run_service import AgentRunService
from arclith import InMemoryRepository
from domain.models.agent_run import AgentRun
from tests.units.conftest import NullLogger


def _make_service() -> AgentRunService:
    return AgentRunService(InMemoryRepository[AgentRun](), NullLogger())


async def test_list_runs_empty():
    router = AgentRunRouter(_make_service(), NullLogger())
    result = await router.list_runs()
    assert result.status == "success"
    assert result.data == []


async def test_list_runs_returns_all():
    service = _make_service()
    await service.create(AgentRun(raw_input = "recette 1"))
    await service.create(AgentRun(raw_input = "recette 2"))
    router = AgentRunRouter(service, NullLogger())
    result = await router.list_runs()
    assert len(result.data) == 2


async def test_list_runs_schema_fields():
    service = _make_service()
    run = await service.create(AgentRun(raw_input = "test"))
    router = AgentRunRouter(service, NullLogger())
    result = await router.list_runs()
    assert len(result.data) == 1
    assert str(result.data[0].uuid) == str(run.uuid)
    assert result.data[0].raw_input == "test"
    assert result.data[0].status == "pending"


async def test_get_run_found():
    service = _make_service()
    run = await service.create(AgentRun(raw_input = "beignets"))
    router = AgentRunRouter(service, NullLogger())
    std_uuid = _uuid.UUID(str(run.uuid))
    result = await router.get_run(std_uuid)
    assert result.status == "success"
    assert str(result.data.uuid) == str(run.uuid)
    assert result.data.raw_input == "beignets"


async def test_get_run_not_found_raises_404():
    router = AgentRunRouter(_make_service(), NullLogger())
    with pytest.raises(HTTPException) as exc_info:
        await router.get_run(_uuid.UUID("00000000-0000-0000-0000-000000000000"))
    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()
