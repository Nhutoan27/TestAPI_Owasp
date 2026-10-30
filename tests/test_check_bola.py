import httpx
import pytest

from app.engine.checks.base import CheckContext
from app.engine.checks.bola import BolaCheck
from app.importers.base import NormalizedEndpoint


def _make_client(status_by_token: dict[str, int]) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        token = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
        status = status_by_token.get(token, 404)
        body = {"id": 1, "secret": "x"} if status == 200 else {"detail": "forbidden"}
        return httpx.Response(status, json=body)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _endpoint() -> NormalizedEndpoint:
    return NormalizedEndpoint(method="GET", path="/users/{id}/orders/{order_id}")


def test_applies_to_get_with_path_param() -> None:
    check = BolaCheck()
    assert check.applies_to(_endpoint()) is True
    assert check.applies_to(NormalizedEndpoint(method="GET", path="/health")) is False
    assert check.applies_to(NormalizedEndpoint(method="POST", path="/users/{id}")) is False


@pytest.mark.asyncio
async def test_bola_vulnerable_endpoint_is_fail() -> None:
    async with _make_client({"token-a": 200, "token-b": 200}) as client:
        context = CheckContext(
            base_url="http://target.local",
            client=client,
            auth_tokens={"user_a": "token-a", "user_b": "token-b"},
        )
        result = await BolaCheck().run(_endpoint(), context)

    assert result.status == "FAIL"
    assert result.owasp_id == "API1:2023"


@pytest.mark.asyncio
async def test_bola_protected_endpoint_is_pass() -> None:
    async with _make_client({"token-a": 200, "token-b": 403}) as client:
        context = CheckContext(
            base_url="http://target.local",
            client=client,
            auth_tokens={"user_a": "token-a", "user_b": "token-b"},
        )
        result = await BolaCheck().run(_endpoint(), context)

    assert result.status == "PASS"


@pytest.mark.asyncio
async def test_bola_missing_auth_profile_is_error() -> None:
    async with _make_client({}) as client:
        context = CheckContext(base_url="http://target.local", client=client, auth_tokens={})
        result = await BolaCheck().run(_endpoint(), context)

    assert result.status == "ERROR"
