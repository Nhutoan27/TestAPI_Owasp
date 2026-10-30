"""Chuan hoa alert tu ZAP va map Confidence -> trang thai, theo CLAUDE.md:

Confidence High/Medium -> FAIL; Confidence Low/False Positive -> NEEDS_REVIEW;
khong co alert -> PASS (truong hop nay xu ly o cap goi ham, vi day la list rong).
"""

from dataclasses import dataclass

from app.core.security import mask_bearer_tokens

_FAIL_CONFIDENCE = {"high", "medium"}
_NEEDS_REVIEW_CONFIDENCE = {"low", "false positive"}

# Theo "Pham vi OWASP" trong CLAUDE.md: injection (SQLi/XSS do ZAP phat hien) gom vao
# OTHER; cac alert con lai cua ZAP chu yeu la loi cau hinh -> API8:2023.
_INJECTION_KEYWORDS = (
    "sql injection",
    "cross site scripting",
    "xss",
    "code injection",
    "command injection",
    "ldap injection",
    "xpath injection",
)


@dataclass
class ZapAlert:
    name: str
    risk: str
    confidence: str
    url: str
    param: str
    description: str
    solution: str
    cwe_id: str
    evidence: str
    status: str  # FAIL | NEEDS_REVIEW
    owasp_id: str


def map_confidence_to_status(confidence: str) -> str:
    normalized = confidence.strip().lower()
    if normalized in _FAIL_CONFIDENCE:
        return "FAIL"
    if normalized in _NEEDS_REVIEW_CONFIDENCE:
        return "NEEDS_REVIEW"
    # Confidence la gia tri khong xac dinh/khong ro: an toan hon la NEEDS_REVIEW thay vi im lang PASS.
    return "NEEDS_REVIEW"


def classify_owasp_id(alert_name: str) -> str:
    name = alert_name.lower()
    if any(keyword in name for keyword in _INJECTION_KEYWORDS):
        return "OTHER"
    return "API8:2023"


def build_zap_alert(raw: dict) -> ZapAlert:
    confidence = raw.get("confidence", "")
    alert_name = raw.get("alert", "")
    return ZapAlert(
        name=alert_name,
        risk=raw.get("risk", ""),
        confidence=confidence,
        url=raw.get("url", ""),
        param=raw.get("param", ""),
        description=raw.get("description", ""),
        solution=raw.get("solution", ""),
        cwe_id=str(raw.get("cweid", "")),
        evidence=mask_bearer_tokens(raw.get("evidence", "")),
        status=map_confidence_to_status(confidence),
        owasp_id=classify_owasp_id(alert_name),
    )
