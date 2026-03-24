from datetime import datetime, timezone

from adapters.input.schemas.agent_run_schema import AgentRunSchema
from domain.models.agent_run import AgentRun


def _now() -> datetime:
    return datetime.now(tz = timezone.utc)


def _make_schema():
    run = AgentRun(raw_input="recette de test")
    return run, AgentRunSchema.model_validate(run, from_attributes=True)


def test_agent_run_schema_uuid():
    from uuid import UUID as StdUUID
    run, schema = _make_schema()
    assert isinstance(schema.uuid, StdUUID)
    assert str(schema.uuid) == str(run.uuid)


def test_agent_run_schema_basic_fields():
    _, schema = _make_schema()
    assert schema.raw_input == "recette de test"
    assert schema.status == "pending"
    assert schema.metadata == {}


def test_agent_run_schema_nullable_fields():
    _, schema = _make_schema()
    assert schema.recipe_uuid is None
    assert schema.recipe_name is None
    assert schema.error is None


def test_agent_run_schema_timestamps():
    _, schema = _make_schema()
    assert isinstance(schema.created_at, datetime)
    assert isinstance(schema.updated_at, datetime)


def test_agent_run_schema_success_entity():
    run = AgentRun(
        raw_input = "carbonara",
        status = "success",
        recipe_uuid = "r-uuid",
        recipe_name = "Carbonara",
        metadata = {"elapsed_ms": 500},
    )
    schema = AgentRunSchema.model_validate(run, from_attributes = True)
    assert schema.status == "success"
    assert schema.recipe_uuid == "r-uuid"
    assert schema.recipe_name == "Carbonara"
    assert schema.metadata["elapsed_ms"] == 500


def test_agent_run_schema_direct_construction():
    now = _now()
    schema = AgentRunSchema(
        uuid = "00000000-0000-0000-0000-000000000001",
        status = "failed",
        raw_input = "test",
        error = "LLM error",
        metadata = {},
        created_at = now,
        updated_at = now,
    )
    assert schema.status == "failed"
    assert schema.error == "LLM error"
