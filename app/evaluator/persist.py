"""Ghi CheckResult / ZapAlert vao DB: test_cases, test_results, evidence, findings.

Chi evaluator moi ghi vao cac bang nay; check (engine/checks/*.py) va zap adapter
(engine/zap/*.py) chi tra ve du lieu thuan, khong tu ghi DB.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Evidence, Finding, TestCase, TestResult
from app.engine.checks.base import CheckResult
from app.engine.zap.alerts import ZapAlert
from app.evaluator.severity import base_severity_for_check_result, base_severity_for_zap_alert


async def get_or_create_test_case(
    db: AsyncSession,
    project_id: int,
    endpoint_id: int | None,
    owasp_id: str,
    check_name: str,
) -> TestCase:
    result = await db.execute(
        select(TestCase).where(
            TestCase.project_id == project_id,
            TestCase.endpoint_id == endpoint_id,
            TestCase.owasp_id == owasp_id,
            TestCase.check_name == check_name,
        )
    )
    test_case = result.scalar_one_or_none()
    if test_case is not None:
        return test_case

    test_case = TestCase(
        project_id=project_id, endpoint_id=endpoint_id, owasp_id=owasp_id, check_name=check_name
    )
    db.add(test_case)
    await db.commit()
    await db.refresh(test_case)
    return test_case


async def _persist_result(
    db: AsyncSession,
    scan_run_id: int,
    test_case_id: int,
    status: str,
    severity_base: str | None,
    evidence_data: dict,
    finding_owasp_id: str,
    finding_title: str,
    finding_description: str,
) -> TestResult:
    test_result = TestResult(
        scan_run_id=scan_run_id,
        test_case_id=test_case_id,
        status=status,
        severity_base=severity_base,
    )
    db.add(test_result)
    await db.flush()  # can test_result.id truoc khi tao evidence/finding

    if evidence_data:
        db.add(Evidence(test_result_id=test_result.id, data=evidence_data))

    if status in ("FAIL", "NEEDS_REVIEW"):
        db.add(
            Finding(
                test_result_id=test_result.id,
                owasp_id=finding_owasp_id,
                title=finding_title,
                description=finding_description,
                severity=severity_base or "Medium",
            )
        )

    await db.commit()
    await db.refresh(test_result)
    return test_result


async def persist_check_result(
    db: AsyncSession, scan_run_id: int, test_case_id: int, result: CheckResult
) -> TestResult:
    return await _persist_result(
        db,
        scan_run_id,
        test_case_id,
        result.status,
        base_severity_for_check_result(result),
        result.evidence,
        result.owasp_id,
        result.name,
        result.description,
    )


async def persist_zap_alert(
    db: AsyncSession, scan_run_id: int, test_case_id: int, alert: ZapAlert
) -> TestResult:
    evidence_data = {"url": alert.url, "param": alert.param, "evidence": alert.evidence}
    return await _persist_result(
        db,
        scan_run_id,
        test_case_id,
        alert.status,
        base_severity_for_zap_alert(alert),
        evidence_data,
        alert.owasp_id,
        alert.name,
        alert.description,
    )
