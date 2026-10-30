import pytest

from app.db import crud
from app.db.models import ScanRun, TestResult as TestResultRow
from app.evaluator.persist import get_or_create_test_case
from app.reports.compare import compare_scan_runs
from app.reports.history import list_scan_runs, summarize_scan_run


async def _make_scan_run(db_session, project_id: int) -> ScanRun:
    scan_run = ScanRun(project_id=project_id, status="completed")
    db_session.add(scan_run)
    await db_session.commit()
    await db_session.refresh(scan_run)
    return scan_run


@pytest.mark.asyncio
async def test_compare_scan_runs_classifies_changes(db_session) -> None:
    project = await crud.create_project(db_session, "cmp-project", "http://localhost:1")

    tc_fixed = await get_or_create_test_case(db_session, project.id, None, "API1:2023", "BOLA")
    tc_regressed = await get_or_create_test_case(db_session, project.id, None, "API5:2023", "BFLA")
    tc_still = await get_or_create_test_case(db_session, project.id, None, "API1:2023", "BOLA-2")

    run1 = await _make_scan_run(db_session, project.id)
    db_session.add_all(
        [
            TestResultRow(scan_run_id=run1.id, test_case_id=tc_fixed.id, status="FAIL"),
            TestResultRow(scan_run_id=run1.id, test_case_id=tc_regressed.id, status="PASS"),
            TestResultRow(scan_run_id=run1.id, test_case_id=tc_still.id, status="FAIL"),
        ]
    )
    await db_session.commit()

    run2 = await _make_scan_run(db_session, project.id)
    db_session.add_all(
        [
            TestResultRow(scan_run_id=run2.id, test_case_id=tc_fixed.id, status="PASS"),
            TestResultRow(scan_run_id=run2.id, test_case_id=tc_regressed.id, status="FAIL"),
            TestResultRow(scan_run_id=run2.id, test_case_id=tc_still.id, status="FAIL"),
        ]
    )
    await db_session.commit()

    comparison = await compare_scan_runs(db_session, run1.id, run2.id)
    changes = {e.test_case_id: e.change for e in comparison.entries}

    assert changes[tc_fixed.id] == "RESOLVED"
    assert changes[tc_regressed.id] == "REGRESSED"
    assert changes[tc_still.id] == "STILL_FAILING"
    assert len(comparison.resolved) == 1
    assert len(comparison.regressed) == 1
    assert len(comparison.still_failing) == 1


@pytest.mark.asyncio
async def test_compare_scan_runs_detects_new_and_removed_test_case(db_session) -> None:
    project = await crud.create_project(db_session, "cmp-project-2", "http://localhost:1")

    tc_old_only = await get_or_create_test_case(db_session, project.id, None, "API1:2023", "BOLA-old")
    tc_new_only = await get_or_create_test_case(db_session, project.id, None, "API1:2023", "BOLA-new")

    run1 = await _make_scan_run(db_session, project.id)
    db_session.add(TestResultRow(scan_run_id=run1.id, test_case_id=tc_old_only.id, status="PASS"))
    await db_session.commit()

    run2 = await _make_scan_run(db_session, project.id)
    db_session.add(TestResultRow(scan_run_id=run2.id, test_case_id=tc_new_only.id, status="FAIL"))
    await db_session.commit()

    comparison = await compare_scan_runs(db_session, run1.id, run2.id)
    changes = {e.test_case_id: e.change for e in comparison.entries}

    assert changes[tc_old_only.id] == "REMOVED"
    assert changes[tc_new_only.id] == "NEW"


@pytest.mark.asyncio
async def test_list_scan_runs_orders_latest_first_and_summarize_counts(db_session) -> None:
    project = await crud.create_project(db_session, "history-project", "http://localhost:1")
    test_case = await get_or_create_test_case(db_session, project.id, None, "API1:2023", "BOLA")

    run1 = await _make_scan_run(db_session, project.id)
    db_session.add(TestResultRow(scan_run_id=run1.id, test_case_id=test_case.id, status="FAIL"))
    await db_session.commit()

    run2 = await _make_scan_run(db_session, project.id)
    db_session.add(TestResultRow(scan_run_id=run2.id, test_case_id=test_case.id, status="PASS"))
    await db_session.commit()

    runs = await list_scan_runs(db_session, project.id)
    assert [r.id for r in runs] == [run2.id, run1.id]

    summary_run1 = await summarize_scan_run(db_session, run1.id)
    assert summary_run1["FAIL"] == 1
    assert summary_run1["PASS"] == 0

    summary_run2 = await summarize_scan_run(db_session, run2.id)
    assert summary_run2["PASS"] == 1
