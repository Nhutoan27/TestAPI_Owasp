from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ScanRun, TestResult


async def list_scan_runs(db: AsyncSession, project_id: int) -> list[ScanRun]:
    result = await db.execute(
        select(ScanRun).where(ScanRun.project_id == project_id).order_by(ScanRun.started_at.desc())
    )
    return list(result.scalars().all())


async def summarize_scan_run(db: AsyncSession, scan_run_id: int) -> dict[str, int]:
    """Dem so test_result theo status (PASS/FAIL/NEEDS_REVIEW/ERROR) cho 1 scan_run."""
    result = await db.execute(select(TestResult.status).where(TestResult.scan_run_id == scan_run_id))
    summary = {"PASS": 0, "FAIL": 0, "NEEDS_REVIEW": 0, "ERROR": 0}
    for (status,) in result.all():
        summary[status] = summary.get(status, 0) + 1
    return summary
