"""Dieu phoi 1 lan scan run: chay custom check (BOLA/BFLA) va ZAP (neu co client),
ghi ket qua qua evaluator. Day la diem noi Importer + Auth Manager + Test Engine +
Evaluator trong luong xu ly ta trong CLAUDE.md.
"""

import asyncio
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.token_provider import get_token
from app.db.models import ApiSpec, AuthProfile, Endpoint, Project, ScanRun
from app.engine.checks.base import BaseCheck, CheckContext
from app.engine.checks.bfla import BflaCheck
from app.engine.checks.bola import BolaCheck
from app.engine.zap.scanner import run_zap_scan
from app.evaluator.persist import get_or_create_test_case, persist_check_result, persist_zap_alert
from app.importers.base import NormalizedEndpoint, NormalizedParameter

logger = logging.getLogger(__name__)

CUSTOM_CHECKS: list[BaseCheck] = [BolaCheck(), BflaCheck()]


def _to_normalized(endpoint: Endpoint) -> NormalizedEndpoint:
    return NormalizedEndpoint(
        method=endpoint.method,
        path=endpoint.path,
        operation_id=endpoint.operation_id,
        summary=endpoint.summary,
        tags=endpoint.tags or [],
        parameters=[
            NormalizedParameter(
                name=p.name, location=p.location, required=p.required, schema_json=p.schema_json
            )
            for p in endpoint.parameters
        ],
    )


async def _latest_api_spec(db: AsyncSession, project_id: int) -> ApiSpec | None:
    result = await db.execute(
        select(ApiSpec)
        .where(ApiSpec.project_id == project_id)
        .order_by(ApiSpec.imported_at.desc())
        .limit(1)
        .options(selectinload(ApiSpec.endpoints).selectinload(Endpoint.parameters))
    )
    return result.scalar_one_or_none()


async def _load_auth_tokens(
    db: AsyncSession, project_id: int, client: httpx.AsyncClient
) -> dict[str, str]:
    result = await db.execute(select(AuthProfile).where(AuthProfile.project_id == project_id))
    tokens: dict[str, str] = {}
    for profile in result.scalars().all():
        try:
            tokens[profile.role] = await get_token(profile, client)
        except Exception:
            logger.exception(
                "Khong lay duoc token cho auth profile '%s' (role=%s)", profile.name, profile.role
            )
    return tokens


async def run_custom_checks(
    db: AsyncSession,
    scan_run_id: int,
    project_id: int,
    endpoints: list[Endpoint],
    context: CheckContext,
) -> None:
    for endpoint in endpoints:
        normalized = _to_normalized(endpoint)
        for check in CUSTOM_CHECKS:
            if not check.applies_to(normalized):
                continue
            test_case = await get_or_create_test_case(
                db, project_id, endpoint.id, check.owasp_id, check.name
            )
            result = await check.run(normalized, context)
            await persist_check_result(db, scan_run_id, test_case.id, result)


async def run_zap_checks(
    db: AsyncSession,
    scan_run_id: int,
    project_id: int,
    zap: object,
    target_base_url: str,
    raw_openapi_content: dict,
) -> None:
    # run_zap_scan la ham dong bo (blocking, co the chay vai phut) -> chay trong
    # thread rieng de khong block event loop cua tien trinh dang goi runner nay.
    alerts = await asyncio.to_thread(run_zap_scan, zap, target_base_url, raw_openapi_content)
    for alert in alerts:
        test_case = await get_or_create_test_case(db, project_id, None, alert.owasp_id, alert.name)
        await persist_zap_alert(db, scan_run_id, test_case.id, alert)


async def run_scan(
    db: AsyncSession,
    project_id: int,
    zap: object | None = None,
    http_client: httpx.AsyncClient | None = None,
    scan_run: ScanRun | None = None,
) -> ScanRun:
    """zap=None de bo qua phan ZAP (vd: chi muon chay nhanh custom check BOLA/BFLA).

    scan_run: truyen vao 1 ScanRun da tao san (vd: endpoint HTTP tao row voi status
    "pending" de tra ve id ngay, roi background task goi run_scan voi row nay) de
    tiep tuc tren cung 1 row, thay vi tu tao row moi.
    """
    project = await db.get(Project, project_id)
    if project is None:
        raise ValueError(f"Project {project_id} not found")

    if scan_run is None:
        scan_run = ScanRun(project_id=project_id, status="running")
        db.add(scan_run)
    else:
        scan_run.status = "running"
    await db.commit()
    await db.refresh(scan_run)

    owns_client = http_client is None
    client = http_client or httpx.AsyncClient()

    try:
        api_spec = await _latest_api_spec(db, project_id)
        endpoints = api_spec.endpoints if api_spec else []
        auth_tokens = await _load_auth_tokens(db, project_id, client)
        context = CheckContext(base_url=project.target_base_url, client=client, auth_tokens=auth_tokens)

        await run_custom_checks(db, scan_run.id, project_id, endpoints, context)

        if zap is not None and api_spec is not None:
            await run_zap_checks(
                db, scan_run.id, project_id, zap, project.target_base_url, api_spec.raw_content
            )

        scan_run.status = "completed"
    except Exception:
        logger.exception("Scan run %s cho project %s bi loi", scan_run.id, project_id)
        scan_run.status = "failed"
        raise
    finally:
        scan_run.finished_at = datetime.now(timezone.utc)
        await db.commit()
        if owns_client:
            await client.aclose()

    return scan_run
