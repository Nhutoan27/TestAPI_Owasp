"""Dieu phoi AI assessment cho 1 finding: mask bang chung -> goi LLM -> validate
output theo schema -> luu ai_assessments + cap nhat severity_ai tren test_result.
"""

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import call_llm_for_severity
from app.ai.schema import SeverityAssessment
from app.core.config import Settings, get_settings
from app.core.security import mask_body
from app.db.models import AiAssessment, Evidence, Finding, TestResult


async def assess_finding(
    db: AsyncSession,
    finding: Finding,
    client: httpx.AsyncClient,
    settings: Settings | None = None,
) -> AiAssessment:
    settings = settings or get_settings()

    evidence_row = (
        await db.execute(select(Evidence).where(Evidence.test_result_id == finding.test_result_id))
    ).scalar_one_or_none()
    evidence_data = mask_body(evidence_row.data) if evidence_row else {}

    finding_context = {
        "owasp_id": finding.owasp_id,
        "title": finding.title,
        "description": finding.description,
        "base_severity": finding.severity,
        "evidence": evidence_data,
    }

    raw_output = await call_llm_for_severity(finding_context, client, settings)
    # Raise neu LLM tra ve sai schema (severity ngoai enum, thieu reasoning, ...):
    # khong bao gio am tham chap nhan 1 severity khong hop le.
    validated = SeverityAssessment.model_validate(raw_output)

    assessment = AiAssessment(
        finding_id=finding.id,
        severity_original=finding.severity,
        severity_suggested=validated.severity,
        reasoning=validated.reasoning,
        raw_output=raw_output,
    )
    db.add(assessment)

    test_result = await db.get(TestResult, finding.test_result_id)
    test_result.severity_ai = validated.severity

    await db.commit()
    await db.refresh(assessment)
    return assessment
