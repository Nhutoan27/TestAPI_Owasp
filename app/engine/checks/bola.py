"""API1:2023 - Broken Object Level Authorization.

So sanh quyen truy cap cung mot object giua user_a va user_b: neu user_b
(khong phai chu object) van lay duoc du lieu (2xx) thi coi la FAIL.
"""

from app.engine.checks.base import BaseCheck, CheckContext, CheckResult, build_url, make_evidence
from app.importers.base import NormalizedEndpoint


class BolaCheck(BaseCheck):
    owasp_id = "API1:2023"
    name = "Broken Object Level Authorization"

    def applies_to(self, endpoint: NormalizedEndpoint) -> bool:
        return endpoint.method == "GET" and "{" in endpoint.path

    async def run(self, endpoint: NormalizedEndpoint, context: CheckContext) -> CheckResult:
        if "user_a" not in context.auth_tokens or "user_b" not in context.auth_tokens:
            return self._error("Can auth profile 'user_a' va 'user_b' de chay BOLA check")

        test_id = context.resolve_test_id(endpoint.path)
        url = build_url(context.base_url, endpoint.path, test_id)

        resp_a = await context.client.get(
            url, headers={"Authorization": f"Bearer {context.auth_tokens['user_a']}"}
        )
        resp_b = await context.client.get(
            url, headers={"Authorization": f"Bearer {context.auth_tokens['user_b']}"}
        )

        evidence = {
            "owner": make_evidence(resp_a, "user_a"),
            "other_user": make_evidence(resp_b, "user_b"),
        }

        if resp_a.status_code == 200 and resp_b.status_code == 200:
            status = "FAIL"
            description = (
                f"user_b truy cap duoc object cua user_a tai {endpoint.method} {endpoint.path} "
                f"(HTTP {resp_b.status_code})."
            )
        elif resp_b.status_code in (401, 403, 404):
            status = "PASS"
            description = f"user_b bi tu choi (HTTP {resp_b.status_code}) khi truy cap object cua user_a."
        else:
            status = "NEEDS_REVIEW"
            description = (
                f"Ket qua khong ro rang: user_a={resp_a.status_code}, user_b={resp_b.status_code}."
            )

        return CheckResult(
            owasp_id=self.owasp_id,
            name=self.name,
            status=status,
            description=description,
            evidence=evidence,
        )
