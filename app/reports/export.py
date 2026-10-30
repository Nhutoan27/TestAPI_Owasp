"""Xuat bao cao cho 1 scan_run: tong hop test_result + finding + ai_assessment."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import AiAssessment, ScanRun, TestCase, TestResult
from app.reports.history import summarize_scan_run


@dataclass
class FindingReportEntry:
    owasp_id: str
    check_name: str
    endpoint_path: str | None
    title: str
    description: str
    status: str
    severity_base: str | None
    severity_ai: str | None
    ai_reasoning: str | None


@dataclass
class ScanReport:
    scan_run_id: int
    project_id: int
    status: str
    started_at: str
    finished_at: str | None
    summary: dict[str, int]
    findings: list[FindingReportEntry]


async def generate_scan_report(db: AsyncSession, scan_run_id: int) -> ScanReport:
    scan_run = await db.get(ScanRun, scan_run_id)
    if scan_run is None:
        raise ValueError(f"ScanRun {scan_run_id} not found")

    summary = await summarize_scan_run(db, scan_run_id)

    result = await db.execute(
        select(TestResult)
        .where(TestResult.scan_run_id == scan_run_id, TestResult.status.in_(("FAIL", "NEEDS_REVIEW")))
        .options(selectinload(TestResult.finding))
    )
    test_results = [tr for tr in result.scalars().all() if tr.finding is not None]

    test_case_ids = [tr.test_case_id for tr in test_results]
    test_cases: dict[int, TestCase] = {}
    if test_case_ids:
        tc_result = await db.execute(
            select(TestCase).where(TestCase.id.in_(test_case_ids)).options(selectinload(TestCase.endpoint))
        )
        test_cases = {tc.id: tc for tc in tc_result.scalars().all()}

    finding_ids = [tr.finding.id for tr in test_results]
    ai_by_finding: dict[int, AiAssessment] = {}
    if finding_ids:
        ai_result = await db.execute(select(AiAssessment).where(AiAssessment.finding_id.in_(finding_ids)))
        for assessment in ai_result.scalars().all():
            ai_by_finding[assessment.finding_id] = assessment

    entries = []
    for tr in test_results:
        tc = test_cases.get(tr.test_case_id)
        ai = ai_by_finding.get(tr.finding.id)
        entries.append(
            FindingReportEntry(
                owasp_id=tr.finding.owasp_id,
                check_name=tc.check_name if tc else "",
                endpoint_path=tc.endpoint.path if tc and tc.endpoint else None,
                title=tr.finding.title,
                description=tr.finding.description,
                status=tr.status,
                severity_base=tr.severity_base,
                severity_ai=tr.severity_ai,
                ai_reasoning=ai.reasoning if ai else None,
            )
        )

    return ScanReport(
        scan_run_id=scan_run.id,
        project_id=scan_run.project_id,
        status=scan_run.status,
        started_at=scan_run.started_at.isoformat(),
        finished_at=scan_run.finished_at.isoformat() if scan_run.finished_at else None,
        summary=summary,
        findings=entries,
    )
