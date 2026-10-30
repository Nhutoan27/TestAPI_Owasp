import pytest

from app.db import crud
from app.db.models import Evidence, Finding
from app.db.models import ScanRun as ScanRunRow
from app.db.models import TestResult as TestResultRow
from app.evaluator.persist import get_or_create_test_case
from app.reports.export import generate_scan_report


@pytest.mark.asyncio
async def test_generate_scan_report_includes_finding_with_endpoint_and_severity(db_session) -> None:
    project = await crud.create_project(db_session, "export-project", "http://localhost:1234")
    normalized_spec = {
        "openapi": "3.0.0",
        "paths": {"/users/{id}": {"get": {"operationId": "getUser"}}},
    }
    from app.importers import openapi as openapi_importer

    normalized = openapi_importer.normalize(normalized_spec)
    api_spec = await crud.save_normalized_spec(
        db_session, project.id, "openapi", normalized_spec, normalized
    )
    endpoint = api_spec.endpoints[0]

    scan_run = ScanRunRow(project_id=project.id, status="completed")
    db_session.add(scan_run)
    await db_session.commit()
    await db_session.refresh(scan_run)

    test_case = await get_or_create_test_case(db_session, project.id, endpoint.id, "API1:2023", "BOLA")
    test_result = TestResultRow(
        scan_run_id=scan_run.id,
        test_case_id=test_case.id,
        status="FAIL",
        severity_base="High",
        severity_ai="Critical",
    )
    db_session.add(test_result)
    await db_session.flush()
    db_session.add(Evidence(test_result_id=test_result.id, data={"url": "http://x/1"}))
    db_session.add(
        Finding(
            test_result_id=test_result.id,
            owasp_id="API1:2023",
            title="BOLA",
            description="leak",
            severity="High",
        )
    )
    await db_session.commit()

    report = await generate_scan_report(db_session, scan_run.id)

    assert report.scan_run_id == scan_run.id
    assert report.summary["FAIL"] == 1
    assert len(report.findings) == 1

    entry = report.findings[0]
    assert entry.owasp_id == "API1:2023"
    assert entry.endpoint_path == "/users/{id}"
    assert entry.severity_base == "High"
    assert entry.severity_ai == "Critical"


@pytest.mark.asyncio
async def test_generate_scan_report_excludes_passing_results(db_session) -> None:
    project = await crud.create_project(db_session, "export-pass-project", "http://localhost:1234")
    scan_run = ScanRunRow(project_id=project.id, status="completed")
    db_session.add(scan_run)
    await db_session.commit()
    await db_session.refresh(scan_run)

    test_case = await get_or_create_test_case(db_session, project.id, None, "API1:2023", "BOLA")
    db_session.add(TestResultRow(scan_run_id=scan_run.id, test_case_id=test_case.id, status="PASS"))
    await db_session.commit()

    report = await generate_scan_report(db_session, scan_run.id)

    assert report.summary["PASS"] == 1
    assert report.findings == []
