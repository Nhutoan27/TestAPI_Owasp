"""JSON schema bat buoc cho output cua LLM khi dieu chinh severity.

AI chi duoc DIEU CHINH severity co so (enum co dinh), khong duoc tu dat gia tri
ngoai thang do, va phai kem reasoning (khong duoc de trong).
"""

from pydantic import BaseModel, field_validator

ALLOWED_SEVERITIES = ("Low", "Medium", "High", "Critical")

SEVERITY_JSON_SCHEMA = {
    "name": "severity_assessment",
    "schema": {
        "type": "object",
        "properties": {
            "severity": {"type": "string", "enum": list(ALLOWED_SEVERITIES)},
            "reasoning": {"type": "string", "minLength": 1},
        },
        "required": ["severity", "reasoning"],
        "additionalProperties": False,
    },
    "strict": True,
}


class SeverityAssessment(BaseModel):
    severity: str
    reasoning: str

    @field_validator("severity")
    @classmethod
    def _validate_severity(cls, value: str) -> str:
        if value not in ALLOWED_SEVERITIES:
            raise ValueError(f"severity '{value}' khong hop le, phai thuoc {ALLOWED_SEVERITIES}")
        return value

    @field_validator("reasoning")
    @classmethod
    def _validate_reasoning(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reasoning khong duoc de trong - AI phai kem ly do khi dieu chinh severity")
        return value
