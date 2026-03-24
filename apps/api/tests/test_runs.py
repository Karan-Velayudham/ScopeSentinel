"""
tests/test_runs.py — Tests for /api/runs endpoints (Epic 1.2.1–1.2.5)
"""

import pytest
from unittest.mock import MagicMock, patch

from db.models import RunStatus, WorkflowRun


# ---------------------------------------------------------------------------
# POST /api/runs
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_trigger_run_success(client, test_user, test_org):
    user, raw_key = test_user

    with patch("routers.runs.run_workflow_task") as mock_task:
        mock_signature = MagicMock()
        mock_task.delay = MagicMock(return_value=None)

        response = await client.post(
            "/api/runs/",
            json={"ticket_id": "SCRUM-1"},
            headers={"X-Api-Key": raw_key},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["ticket_id"] == "SCRUM-1"
    assert data["status"] == "PENDING"
    assert "run_id" in data
    assert data["dry_run"] is False
    mock_task.delay.assert_called_once()


@pytest.mark.asyncio
async def test_trigger_run_dry_run(client, test_user):
    user, raw_key = test_user

    with patch("routers.runs.run_workflow_task") as mock_task:
        mock_task.delay = MagicMock(return_value=None)

        response = await client.post(
            "/api/runs/",
            json={"ticket_id": "SCRUM-2", "dry_run": True},
            headers={"X-Api-Key": raw_key},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["dry_run"] is True
    assert data["status"] == "PENDING"


@pytest.mark.asyncio
async def test_trigger_run_unauthorized(client):
    response = await client.post(
        "/api/runs/",
        json={"ticket_id": "SCRUM-1"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_trigger_run_invalid_api_key(client):
    response = await client.post(
        "/api/runs/",
        json={"ticket_id": "SCRUM-1"},
        headers={"X-Api-Key": "totally-wrong-key"},
    )
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/runs
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_runs_empty(client, test_user):
    user, raw_key = test_user
    response = await client.get("/api/runs/", headers={"X-Api-Key": raw_key})
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["meta"]["total"] == 0


@pytest.mark.asyncio
async def test_list_runs_with_data(client, test_user, test_session, test_org):
    user, raw_key = test_user

    # Create two runs directly in DB
    run1 = WorkflowRun(org_id=test_org.id, ticket_id="SCRUM-10", status=RunStatus.SUCCEEDED)
    run2 = WorkflowRun(org_id=test_org.id, ticket_id="SCRUM-11", status=RunStatus.RUNNING)
    test_session.add(run1)
    test_session.add(run2)
    await test_session.commit()

    response = await client.get("/api/runs/", headers={"X-Api-Key": raw_key})
    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_runs_status_filter(client, test_user, test_session, test_org):
    user, raw_key = test_user

    run1 = WorkflowRun(org_id=test_org.id, ticket_id="SCRUM-20", status=RunStatus.SUCCEEDED)
    run2 = WorkflowRun(org_id=test_org.id, ticket_id="SCRUM-21", status=RunStatus.FAILED)
    test_session.add(run1)
    test_session.add(run2)
    await test_session.commit()

    response = await client.get(
        "/api/runs/?status=succeeded",
        headers={"X-Api-Key": raw_key},
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["status"] == "SUCCEEDED"


# ---------------------------------------------------------------------------
# GET /api/runs/{id}
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_run_not_found(client, test_user):
    user, raw_key = test_user
    response = await client.get(
        "/api/runs/nonexistent-id",
        headers={"X-Api-Key": raw_key},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_run_detail(client, test_user, test_session, test_org):
    user, raw_key = test_user

    run = WorkflowRun(org_id=test_org.id, ticket_id="SCRUM-30", status=RunStatus.RUNNING)
    test_session.add(run)
    await test_session.commit()
    await test_session.refresh(run)

    response = await client.get(
        f"/api/runs/{run.id}",
        headers={"X-Api-Key": raw_key},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == run.id
    assert data["ticket_id"] == "SCRUM-30"
    assert data["status"] == "RUNNING"
    assert data["steps"] == []
    assert data["hitl_events"] == []


# ---------------------------------------------------------------------------
# GET /api/runs/{id}/plan
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_plan_no_plan_yet(client, test_user, test_session, test_org):
    user, raw_key = test_user

    run = WorkflowRun(org_id=test_org.id, ticket_id="SCRUM-40", status=RunStatus.PENDING)
    test_session.add(run)
    await test_session.commit()
    await test_session.refresh(run)

    response = await client.get(
        f"/api/runs/{run.id}/plan",
        headers={"X-Api-Key": raw_key},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == run.id
    assert data["plan"] is None


@pytest.mark.asyncio
async def test_get_plan_with_plan(client, test_user, test_session, test_org):
    import json
    user, raw_key = test_user

    plan_data = {"steps": ["Step 1", "Step 2"], "architecture_notes": "Use FastAPI"}
    run = WorkflowRun(
        org_id=test_org.id,
        ticket_id="SCRUM-41",
        status=RunStatus.WAITING_HITL,
        plan_json=json.dumps(plan_data),
    )
    test_session.add(run)
    await test_session.commit()
    await test_session.refresh(run)

    response = await client.get(
        f"/api/runs/{run.id}/plan",
        headers={"X-Api-Key": raw_key},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["plan"]["steps"] == ["Step 1", "Step 2"]


# ---------------------------------------------------------------------------
# POST /api/runs/{id}/decision
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_submit_decision_not_waiting(client, test_user, test_session, test_org):
    user, raw_key = test_user

    run = WorkflowRun(org_id=test_org.id, ticket_id="SCRUM-50", status=RunStatus.RUNNING)
    test_session.add(run)
    await test_session.commit()
    await test_session.refresh(run)

    response = await client.post(
        f"/api/runs/{run.id}/decision",
        json={"action": "approve"},
        headers={"X-Api-Key": raw_key},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_submit_decision_modify_requires_feedback(client, test_user, test_session, test_org):
    user, raw_key = test_user

    run = WorkflowRun(org_id=test_org.id, ticket_id="SCRUM-51", status=RunStatus.WAITING_HITL)
    test_session.add(run)
    await test_session.commit()
    await test_session.refresh(run)

    response = await client.post(
        f"/api/runs/{run.id}/decision",
        json={"action": "modify"},  # Missing feedback
        headers={"X-Api-Key": raw_key},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_submit_decision_approve(client, test_user, test_session, test_org):
    user, raw_key = test_user

    run = WorkflowRun(org_id=test_org.id, ticket_id="SCRUM-52", status=RunStatus.WAITING_HITL)
    test_session.add(run)
    await test_session.commit()
    await test_session.refresh(run)

    with patch("routers.runs.aioredis.from_url") as mock_redis_cls:
        mock_redis = MagicMock()
        mock_redis.publish = MagicMock(return_value=None)
        mock_redis.aclose = MagicMock(return_value=None)

        # Make the async mock work
        from unittest.mock import AsyncMock
        mock_redis.publish = AsyncMock()
        mock_redis.aclose = AsyncMock()
        mock_redis_cls.return_value = mock_redis

        response = await client.post(
            f"/api/runs/{run.id}/decision",
            json={"action": "approve"},
            headers={"X-Api-Key": raw_key},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert data["action"] == "approve"
    mock_redis.publish.assert_awaited_once()
