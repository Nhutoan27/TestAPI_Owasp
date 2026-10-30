"""Khung chung cho custom check: moi check la 1 file, ke thua BaseCheck.

Them check moi: tao file trong engine/checks/, khong sua runner (runner se
tu nap cac BaseCheck khi duoc xay dung o buoc tiep theo cua lo trinh).
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import httpx

from app.core.security import mask_body, mask_headers
from app.importers.base import NormalizedEndpoint

_PATH_PARAM_RE = re.compile(r"\{[^}]+\}")


@dataclass
class CheckContext:
    base_url: str
    client: httpx.AsyncClient
    auth_tokens: dict[str, str] = field(default_factory=dict)  # role -> bearer token
    # shortcut: id mau de thay vao path param khi khong co test_cases/seed data rieng,
    # nang cap: lay tu bang test_cases khi runner/evaluator duoc xay dung.
    object_ids: dict[str, str] = field(default_factory=dict)
    default_object_id: str = "1"

    def resolve_test_id(self, path: str) -> str:
        return self.object_ids.get(path, self.default_object_id)


@dataclass
class CheckResult:
    owasp_id: str
    name: str
    status: str  # PASS | FAIL | NEEDS_REVIEW | ERROR
    description: str
    evidence: dict


def build_url(base_url: str, path: str, test_id: str) -> str:
    filled_path = _PATH_PARAM_RE.sub(str(test_id), path)
    return base_url.rstrip("/") + filled_path


def make_evidence(response: httpx.Response, auth_profile_used: str) -> dict:
    """Bang chung da mask token/body nhay cam, an toan de luu log / gui len LLM."""
    request = response.request
    body = None
    try:
        body = mask_body(response.json())
    except ValueError:
        body = None

    return {
        "auth_profile_used": auth_profile_used,
        "request": {
            "method": request.method,
            "url": str(request.url),
            "headers": mask_headers(dict(request.headers)),
        },
        "response": {
            "status_code": response.status_code,
            "body": body,
        },
    }


class BaseCheck(ABC):
    owasp_id: str
    name: str

    @abstractmethod
    def applies_to(self, endpoint: NormalizedEndpoint) -> bool: ...

    @abstractmethod
    async def run(self, endpoint: NormalizedEndpoint, context: CheckContext) -> CheckResult: ...

    def _error(self, message: str) -> CheckResult:
        return CheckResult(
            owasp_id=self.owasp_id,
            name=self.name,
            status="ERROR",
            description=message,
            evidence={},
        )
