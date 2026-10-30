import pytest
from sqlalchemy import select

from app.db import crud
from app.db.models import Evidence, Finding, ScanRun
from app.engine.checks.base import CheckResult
from app.evaluator.persist import get_or_create_test_case, persist_check_result


async def _make_scan_run(db_session, project_id: int) -> ScanRun:
    scan_run = ScanRun(project_id=project_id, status="running")
    db_session.add(scan_run)
    await db_session.commit()
    await db_session.refresh(scan_run)
    return scan_run


@pytest.mark.asyncio
async def test_get_or_create_test_case_is_idempotent(db_session) -> None:
    project = await crud.create_project(db_session, "p-evaluator-1", "http://localhost:1234")

    tc1 = await get_or_create_test_case(db_session, project.id, None, "API1:2023", "BOLA")
    tc2 = await get_or_create_test_case(db_session, project.id, None, "API1:2023", "BOLA")

    assert tc1.id == tc2.id


@pytest.mark.asyncio
async def test_persist_fail_result_creates_evidence_and_finding(db_session) -> None:
    project = await crud.create_project(db_session, "p-evaluator-2", "http://localhost:1234")
    scan_run = await _make_scan_run(db_session, project.id)
    test_case = await get_or_create_test_case(db_session, project.id, None, "API1:2023", "BOLA")

    result = CheckResult(
        owasp_id="API1:2023", name="BOLA", status="FAIL", description="leak", evidence={"a": 1}
    )
    test_result = await persist_check_result(db_session, scan_run.id, test_case.id, result)

    assert test_result.status == "FAIL"
    assert test_result.severity_base == "High"

    evidence = (
        await db_session.execute(select(Evidence).where(Evidence.test_result_id == test_result.id))
    ).scalar_one()
    assert evidence.data == {"a": 1}

    finding = (
        await db_session.execute(select(Finding).where(Finding.test_result_id == test_result.id))
    ).scalar_one()
    assert finding.severity == "High"
    assert finding.owasp_id == "API1:2023"


@pytest.mark.asyncio
async def test_persist_pass_result_has_no_finding(db_session) -> None:
    project = await crud.create_project(db_session, "p-evaluator-3", "http://localhost:1234")
    scan_run = await _make_scan_run(db_session, project.id)
    test_case = await get_or_create_test_case(db_session, project.id, None, "API1:2023", "BOLA")

    result = CheckResult(
        owasp_id="API1:2023", name="BOLA", status="PASS", description="ok", evidence={"a": 1}
    )
    test_result = await persist_check_result(db_session, scan_run.id, test_case.id, result)

    assert test_result.severity_base is None
    finding = (
        await db_session.execute(select(Finding).where(Finding.test_result_id == test_result.id))
    ).scalar_one_or_none()
    assert finding is None
