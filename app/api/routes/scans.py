import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.ai.analyzer import assess_finding
from app.core.config import Settings, get_settings
from app.db import crud
from app.db.models import Finding, ScanRun, TestResult
from app.db.session import get_db
from app.engine.runner import run_scan
from app.reports.compare import compare_scan_runs
from app.reports.export import generate_scan_report
from app.reports.history import list_scan_runs, summarize_scan_run
from app.schemas.scan import (
    AiAssessmentOut,
    ScanComparisonOut,
    ScanReportOut,
    ScanRunOut,
    ScanRunSummaryOut,
)

router = APIRouter(tags=["scans"])


async def _run_scan_in_background(project_id: int, scan_run_id: int, settings: Settings) -> None:
    # Tao engine rieng cho background task (khong dung chung engine global cua
    # app.db.session): asyncpg pool gan voi 1 event loop, ma BackgroundTasks co
    # the chay tren context loop khac voi request goc.
    engine = create_async_engine(settings.database_url)
    try:
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as db:
            scan_run = await db.get(ScanRun, scan_run_id)
            async with httpx.AsyncClient() as client:
                await run_scan(db, project_id, zap=None, http_client=client, scan_run=scan_run)
    finally:
        await engine.dispose()


@router.post(
    "/projects/{project_id}/scans", response_model=ScanRunOut, status_code=status.HTTP_202_ACCEPTED
)
async def trigger_scan(
    project_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ScanRunOut:
    """Tao ScanRun ngay (status=pending) va chay thuc te trong background task,
    theo yeu cau "scan chay nen, khong chay dong bo trong request HTTP"."""
    project = await crud.get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    scan_run = ScanRun(project_id=project_id, status="pending")
    db.add(scan_run)
    await db.commit()
    await db.refresh(scan_run)

    background_tasks.add_task(_run_scan_in_background, project_id, scan_run.id, settings)
    return ScanRunOut.model_validate(scan_run)


@router.get("/projects/{project_id}/scans", response_model=list[ScanRunOut])
async def get_scan_history(project_id: int, db: AsyncSession = Depends(get_db)) -> list[ScanRunOut]:
    runs = await list_scan_runs(db, project_id)
    return [ScanRunOut.model_validate(r) for r in runs]


@router.get("/scans/{scan_run_id}", response_model=ScanRunSummaryOut)
async def get_scan_run(scan_run_id: int, db: AsyncSession = Depends(get_db)) -> ScanRunSummaryOut:
    scan_run = await db.get(ScanRun, scan_run_id)
    if scan_run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ScanRun not found")
    summary = await summarize_scan_run(db, scan_run_id)
    return ScanRunSummaryOut(**ScanRunOut.model_validate(scan_run).model_dump(), summary=summary)


@router.get("/scans/{scan_run_id}/report", response_model=ScanReportOut)
async def get_scan_report(scan_run_id: int, db: AsyncSession = Depends(get_db)) -> ScanReportOut:
    try:
        report = await generate_scan_report(db, scan_run_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ScanReportOut.model_validate(report)


@router.get("/scans/compare", response_model=ScanComparisonOut)
async def compare_scans(old: int, new: int, db: AsyncSession = Depends(get_db)) -> ScanComparisonOut:
    comparison = await compare_scan_runs(db, old, new)
    return ScanComparisonOut.model_validate(comparison)


@router.post("/scans/{scan_run_id}/ai-assess", response_model=list[AiAssessmentOut])
async def ai_assess_scan_run(
    scan_run_id: int,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list[AiAssessmentOut]:
    result = await db.execute(
        select(Finding).join(TestResult).where(TestResult.scan_run_id == scan_run_id)
    )
    findings = result.scalars().all()
    if not findings:
        return []

    assessments = []
    async with httpx.AsyncClient() as client:
        for finding in findings:
            assessments.append(await assess_finding(db, finding, client, settings))
    return [AiAssessmentOut.model_validate(a) for a in assessments]
