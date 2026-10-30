from datetime import datetime

from pydantic import BaseModel


class ScanRunOut(BaseModel):
    id: int
    project_id: int
    status: str
    started_at: datetime
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class ScanRunSummaryOut(ScanRunOut):
    summary: dict[str, int]


class FindingReportOut(BaseModel):
    owasp_id: str
    check_name: str
    endpoint_path: str | None
    title: str
    description: str
    status: str
    severity_base: str | None
    severity_ai: str | None
    ai_reasoning: str | None

    model_config = {"from_attributes": True}


class ScanReportOut(BaseModel):
    scan_run_id: int
    project_id: int
    status: str
    started_at: str
    finished_at: str | None
    summary: dict[str, int]
    findings: list[FindingReportOut]

    model_config = {"from_attributes": True}


class ComparisonEntryOut(BaseModel):
    test_case_id: int
    owasp_id: str
    check_name: str
    old_status: str | None
    new_status: str | None
    change: str

    model_config = {"from_attributes": True}


class ScanComparisonOut(BaseModel):
    old_scan_run_id: int
    new_scan_run_id: int
    entries: list[ComparisonEntryOut]

    model_config = {"from_attributes": True}


class AiAssessmentOut(BaseModel):
    id: int
    finding_id: int
    severity_original: str
    severity_suggested: str
    reasoning: str

    model_config = {"from_attributes": True}
