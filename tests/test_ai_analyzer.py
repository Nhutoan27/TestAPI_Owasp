import json

import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.ai.analyzer import assess_finding
from app.db import crud
from app.db.models import AiAssessment, Evidence, Finding
from app.db.models import ScanRun as ScanRunRow
from app.db.models import TestResult as TestResultRow
from app.evaluator.persist import get_or_create_test_case


def _llm_client(response_content: str) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": response_content}}]})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def _seed_finding(db_session, name: str, evidence_data: dict) -> Finding:
    project = await crud.create_project(db_session, name, "http://localhost:1234")
    scan_run = ScanRunRow(project_id=project.id, status="completed")
    db_session.add(scan_run)
    await db_session.commit()
    await db_session.refresh(scan_run)

    test_case = await get_or_create_test_case(db_session, project.id, None, "API1:2023", "BOLA")
    test_result = TestResultRow(
        scan_run_id=scan_run.id, test_case_id=test_case.id, status="FAIL", severity_base="High"
    )
    db_session.add(test_result)
    await db_session.flush()

    db_session.add(Evidence(test_result_id=test_result.id, data=evidence_data))
    finding = Finding(
        test_result_id=test_result.id,
        owasp_id="API1:2023",
        title="BOLA",
        description="user_b truy cap duoc object cua user_a",
        severity="High",
    )
    db_session.add(finding)
    await db_session.commit()
    await db_session.refresh(finding)
    return finding


@pytest.mark.asyncio
async def test_assess_finding_persists_assessment_and_updates_test_result(db_session) -> None:
    finding = await _seed_finding(db_session, "ai-ok-project", {"url": "http://x/1"})

    llm_response = json.dumps({"severity": "Critical", "reasoning": "Du lieu nhay cam bi lo"})
    async with _llm_client(llm_response) as client:
        assessment = await assess_finding(db_session, finding, client)

    assert assessment.severity_original == "High"
    assert assessment.severity_suggested == "Critical"
    assert assessment.reasoning == "Du lieu nhay cam bi lo"

    stored = (
        await db_session.execute(select(AiAssessment).where(AiAssessment.finding_id == finding.id))
    ).scalar_one()
    assert stored.severity_suggested == "Critical"

    test_result = await db_session.get(TestResultRow, finding.test_result_id)
    assert test_result.severity_ai == "Critical"
    assert test_result.severity_base == "High"  # severity goc khong bi ghi de


@pytest.mark.asyncio
async def test_assess_finding_rejects_invalid_severity_from_llm(db_session) -> None:
    finding = await _seed_finding(db_session, "ai-invalid-project", {"url": "http://x/1"})

    llm_response = json.dumps({"severity": "Super High", "reasoning": "khong hop le"})
    async with _llm_client(llm_response) as client:
        with pytest.raises(ValidationError):
            await assess_finding(db_session, finding, client)

    stored = (
        await db_session.execute(select(AiAssessment).where(AiAssessment.finding_id == finding.id))
    ).scalar_one_or_none()
    assert stored is None

    test_result = await db_session.get(TestResultRow, finding.test_result_id)
    assert test_result.severity_ai is None


@pytest.mark.asyncio
async def test_assess_finding_rejects_empty_reasoning(db_session) -> None:
    finding = await _seed_finding(db_session, "ai-empty-reason-project", {"url": "http://x/1"})

    llm_response = json.dumps({"severity": "Medium", "reasoning": "   "})
    async with _llm_client(llm_response) as client:
        with pytest.raises(ValidationError):
            await assess_finding(db_session, finding, client)


@pytest.mark.asyncio
async def test_assess_finding_masks_bearer_token_before_sending_to_llm(db_session) -> None:
    evidence_data = {
        "request": {"headers": {"Authorization": "Bearer super-secret-token"}},
        "response": {"body": {"password": "pa$$w0rd"}},
    }
    finding = await _seed_finding(db_session, "ai-mask-project", evidence_data)

    captured_bodies: list[bytes] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_bodies.append(request.content)
        content = json.dumps({"severity": "High", "reasoning": "ok"})
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await assess_finding(db_session, finding, client)

    sent_text = captured_bodies[0].decode("utf-8")
    assert "super-secret-token" not in sent_text
    assert "pa$$w0rd" not in sent_text
