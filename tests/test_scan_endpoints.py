import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.db.models import Project, ScanRun
from app.main import app


@pytest.mark.asyncio
async def test_trigger_scan_and_fetch_report_end_to_end() -> None:
    """Project khong co endpoint/auth-profile -> run_scan hoan tat sach, khong can
    target thuc. Muc tieu la kiem tra noi HTTP (status code, response shape,
    background task thuc su chay), logic BOLA/BFLA da duoc test rieng trong
    test_runner.py voi target gia lap."""
    project_id = None
    scan_run_id = None
    try:
        with TestClient(app) as client:
            create_resp = client.post(
                "/projects",
                json={"name": "http-scan-project", "target_base_url": "http://localhost:9999"},
            )
            assert create_resp.status_code == 201
            project_id = create_resp.json()["id"]

            trigger_resp = client.post(f"/projects/{project_id}/scans")
            assert trigger_resp.status_code == 202
            scan_run_id = trigger_resp.json()["id"]

            status_resp = client.get(f"/scans/{scan_run_id}")
            assert status_resp.status_code == 200
            body = status_resp.json()
            assert body["status"] == "completed"
            assert body["summary"] == {"PASS": 0, "FAIL": 0, "NEEDS_REVIEW": 0, "ERROR": 0}

            report_resp = client.get(f"/scans/{scan_run_id}/report")
            assert report_resp.status_code == 200
            assert report_resp.json()["findings"] == []

            history_resp = client.get(f"/projects/{project_id}/scans")
            assert history_resp.status_code == 200
            assert len(history_resp.json()) == 1
    finally:
        engine = create_async_engine(get_settings().database_url)
        try:
            async with engine.begin() as conn:
                if scan_run_id is not None:
                    await conn.execute(delete(ScanRun).where(ScanRun.id == scan_run_id))
                if project_id is not None:
                    await conn.execute(delete(Project).where(Project.id == project_id))
        finally:
            await engine.dispose()
