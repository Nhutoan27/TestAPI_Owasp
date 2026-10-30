"""Severity co so: do rule xac dinh, AI (buoc 5) chi duoc dieu chinh sau nay.

Chi assign severity cho FAIL/NEEDS_REVIEW. PASS/ERROR khong co finding nen
khong can severity.
"""

from app.engine.checks.base import CheckResult
from app.engine.zap.alerts import ZapAlert

_CHECK_BASE_SEVERITY: dict[tuple[str, str], str] = {
    ("API1:2023", "FAIL"): "High",
    ("API1:2023", "NEEDS_REVIEW"): "Medium",
    ("API5:2023", "FAIL"): "High",
    ("API5:2023", "NEEDS_REVIEW"): "Medium",
}

_ZAP_RISK_TO_SEVERITY: dict[str, str] = {
    "informational": "Low",
    "low": "Low",
    "medium": "Medium",
    "high": "High",
}


def base_severity_for_check_result(result: CheckResult) -> str | None:
    if result.status not in ("FAIL", "NEEDS_REVIEW"):
        return None
    return _CHECK_BASE_SEVERITY.get((result.owasp_id, result.status), "Medium")


def base_severity_for_zap_alert(alert: ZapAlert) -> str:
    return _ZAP_RISK_TO_SEVERITY.get(alert.risk.strip().lower(), "Medium")
