"""Ham mask chung: che token/mat khau/cookie/PII truoc khi log hoac gui len LLM."""

import re

# 1 bo key nhay cam dung chung cho ca header va body: mask_body (de quy) va mask_headers
# (dict header dep) phai cung nhin ra "authorization" lan "password" o bat ky dau.
_SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "password",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "api_key",
}

MASK = "***MASKED***"


def mask_headers(headers: dict[str, str]) -> dict[str, str]:
    return {key: (MASK if key.lower() in _SENSITIVE_KEYS else value) for key, value in headers.items()}


def mask_body(body: object) -> object:
    """Mask de quy cac key nhay cam trong dict/list. Gia tri khac giu nguyen."""
    if isinstance(body, dict):
        return {
            key: (MASK if key.lower() in _SENSITIVE_KEYS else mask_body(value))
            for key, value in body.items()
        }
    if isinstance(body, list):
        return [mask_body(item) for item in body]
    return body


def mask_target_allowlist_check(host: str, allowed_hosts: list[str]) -> bool:
    """True neu host nam trong allowlist (so khop khong phan biet hoa/thuong)."""
    return host.strip().lower() in allowed_hosts


_BEARER_RE = re.compile(r"Bearer\s+\S+", re.IGNORECASE)


def mask_bearer_tokens(text: str) -> str:
    return _BEARER_RE.sub(f"Bearer {MASK}", text)
