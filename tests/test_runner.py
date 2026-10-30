import httpx
import pytest
from sqlalchemy import select

from app.db import crud
from app.db.models import TestResult as TestResultRow
from app.engine.runner import run_scan
from app.importers import openapi as openapi_importer

_OPENAPI_SPEC = {
    "openapi": "3.0.0",
    "paths": {
        "/users/{id}": {
            "get": {
                "operationId": "getUser",
                "parameters": [
                    {"name": "id", "in": "path", "required": True, "schema": {"type": "integer"}}
                ],
            }
        }
    },
}


def _make_client(status_by_token: dict[str, int]) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        token = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
        status = status_by_token.get(token, 404)
        body = {"id": 1} if status == 200 else {"detail": "forbidden"}
        return httpx.Response(status, json=body)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def _seed_project_with_spec_and_profiles(db_session, name: str):
    project = await crud.create_project(db_session, name, "http://localhost:9999")
    normalized = openapi_importer.normalize(_OPENAPI_SPEC)
    await crud.save_normalized_spec(db_session, project.id, "openapi", _OPENAPI_SPEC, normalized)
    await crud.create_auth_profile(
        db_session, project.id, "User A", "user_a", None, {}, "access_token", "token-a"
    )
    await crud.create_auth_profile(
        db_session, project.id, "User B", "user_b", None, {}, "access_token", "token-b"
    )
    return project


@pytest.mark.asyncio
async def test_run_scan_detects_bola_vulnerability(db_session) -> None:
    project = await _seed_project_with_spec_and_profiles(db_session, "runner-bola-vuln")

    async with _make_client({"token-a": 200, "token-b": 200}) as client:
        scan_run = await run_scan(db_session, project.id, zap=None, http_client=client)

    assert scan_run.status == "completed"

    results = (
        await db_session.execute(select(TestResultRow).where(TestResultRow.scan_run_id == scan_run.id))
    ).scalars().all()
    assert len(results) == 1
    assert results[0].status == "FAIL"
    assert results[0].severity_base == "High"


@pytest.mark.asyncio
async def test_run_scan_without_vulnerability_is_pass(db_session) -> None:
    project = await _seed_project_with_spec_and_profiles(db_session, "runner-bola-safe")

    async with _make_client({"token-a": 200, "token-b": 403}) as client:
        scan_run = await run_scan(db_session, project.id, zap=None, http_client=client)

    results = (
        await db_session.execute(select(TestResultRow).where(TestResultRow.scan_run_id == scan_run.id))
    ).scalars().all()
    assert len(results) == 1
    assert results[0].status == "PASS"
    assert results[0].severity_base is None
