import httpx
import pytest

from app.engine.checks.base import CheckContext
from app.engine.checks.bfla import BflaCheck
from app.importers.base import NormalizedEndpoint


def _make_client(status_code: int) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        body = {"ok": True} if status_code < 300 else {"detail": "forbidden"}
        return httpx.Response(status_code, json=body)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _admin_endpoint() -> NormalizedEndpoint:
    return NormalizedEndpoint(method="DELETE", path="/admin/users/{id}")


def test_applies_to_admin_path_only() -> None:
    check = BflaCheck()
    assert check.applies_to(_admin_endpoint()) is True
    assert check.applies_to(NormalizedEndpoint(method="GET", path="/users/{id}")) is False
    assert check.applies_to(NormalizedEndpoint(method="GET", path="/reports", tags=["Admin"])) is True


@pytest.mark.asyncio
async def test_bfla_non_admin_can_call_admin_endpoint_is_fail() -> None:
    async with _make_client(200) as client:
        context = CheckContext(
            base_url="http://target.local", client=client, auth_tokens={"user_a": "token-a"}
        )
        result = await BflaCheck().run(_admin_endpoint(), context)

    assert result.status == "FAIL"
    assert result.owasp_id == "API5:2023"


@pytest.mark.asyncio
async def test_bfla_non_admin_blocked_is_pass() -> None:
    async with _make_client(403) as client:
        context = CheckContext(
            base_url="http://target.local", client=client, auth_tokens={"user_a": "token-a"}
        )
        result = await BflaCheck().run(_admin_endpoint(), context)

    assert result.status == "PASS"


@pytest.mark.asyncio
async def test_bfla_missing_auth_profile_is_error() -> None:
    async with _make_client(403) as client:
        context = CheckContext(base_url="http://target.local", client=client, auth_tokens={})
        result = await BflaCheck().run(_admin_endpoint(), context)

    assert result.status == "ERROR"
