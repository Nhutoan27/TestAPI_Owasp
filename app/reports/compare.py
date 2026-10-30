"""So sanh 2 scan_run cua cung 1 project: test_case nao moi xuat hien, da fix,
bi regress (truoc PASS gio FAIL/NEEDS_REVIEW), hay van dang loi.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TestCase, TestResult

_ISSUE_STATUSES = {"FAIL", "NEEDS_REVIEW"}


@dataclass
class ComparisonEntry:
    test_case_id: int
    owasp_id: str
    check_name: str
    old_status: str | None
    new_status: str | None
    change: str  # NEW | REMOVED | RESOLVED | REGRESSED | STILL_FAILING | UNCHANGED


@dataclass
class ScanComparison:
    old_scan_run_id: int
    new_scan_run_id: int
    entries: list[ComparisonEntry]

    @property
    def regressed(self) -> list[ComparisonEntry]:
        return [e for e in self.entries if e.change == "REGRESSED"]

    @property
    def resolved(self) -> list[ComparisonEntry]:
        return [e for e in self.entries if e.change == "RESOLVED"]

    @property
    def still_failing(self) -> list[ComparisonEntry]:
        return [e for e in self.entries if e.change == "STILL_FAILING"]


def _classify(old_status: str | None, new_status: str | None) -> str:
    if old_status is None and new_status is not None:
        return "NEW"
    if old_status is not None and new_status is None:
        return "REMOVED"

    old_is_issue = old_status in _ISSUE_STATUSES
    new_is_issue = new_status in _ISSUE_STATUSES

    if old_is_issue and not new_is_issue:
        return "RESOLVED"
    if not old_is_issue and new_is_issue:
        return "REGRESSED"
    if old_is_issue and new_is_issue:
        return "STILL_FAILING"
    return "UNCHANGED"


async def _status_by_test_case(db: AsyncSession, scan_run_id: int) -> dict[int, str]:
    result = await db.execute(
        select(TestResult.test_case_id, TestResult.status).where(TestResult.scan_run_id == scan_run_id)
    )
    return {test_case_id: status for test_case_id, status in result.all()}


async def compare_scan_runs(
    db: AsyncSession, old_scan_run_id: int, new_scan_run_id: int
) -> ScanComparison:
    old_map = await _status_by_test_case(db, old_scan_run_id)
    new_map = await _status_by_test_case(db, new_scan_run_id)

    test_case_ids = sorted(set(old_map) | set(new_map))
    if not test_case_ids:
        return ScanComparison(old_scan_run_id, new_scan_run_id, [])

    result = await db.execute(select(TestCase).where(TestCase.id.in_(test_case_ids)))
    test_cases = {tc.id: tc for tc in result.scalars().all()}

    entries = [
        ComparisonEntry(
            test_case_id=tc_id,
            owasp_id=test_cases[tc_id].owasp_id,
            check_name=test_cases[tc_id].check_name,
            old_status=old_map.get(tc_id),
            new_status=new_map.get(tc_id),
            change=_classify(old_map.get(tc_id), new_map.get(tc_id)),
        )
        for tc_id in test_case_ids
    ]
    return ScanComparison(old_scan_run_id, new_scan_run_id, entries)
