"""API5:2023 - Broken Function Level Authorization.

Goi mot endpoint duoc coi la chi danh cho admin (path/tags co chua "admin")
bang token cua user_a (khong phai admin). Neu van thanh cong (2xx) thi FAIL.
"""

from app.engine.checks.base import BaseCheck, CheckContext, CheckResult, build_url, make_evidence
from app.importers.base import NormalizedEndpoint


class BflaCheck(BaseCheck):
    owasp_id = "API5:2023"
    name = "Broken Function Level Authorization"

    def applies_to(self, endpoint: NormalizedEndpoint) -> bool:
        haystack = f"{endpoint.path} {' '.join(endpoint.tags)}".lower()
        return "admin" in haystack

    async def run(self, endpoint: NormalizedEndpoint, context: CheckContext) -> CheckResult:
        if "user_a" not in context.auth_tokens:
            return self._error("Can auth profile 'user_a' (khong phai admin) de chay BFLA check")

        test_id = context.resolve_test_id(endpoint.path)
        url = build_url(context.base_url, endpoint.path, test_id)

        resp = await context.client.request(
            endpoint.method,
            url,
            headers={"Authorization": f"Bearer {context.auth_tokens['user_a']}"},
        )

        evidence = {"non_admin_attempt": make_evidence(resp, "user_a")}

        if resp.status_code in (401, 403):
            status = "PASS"
            description = f"user_a (khong phai admin) bi tu choi (HTTP {resp.status_code})."
        elif 200 <= resp.status_code < 300:
            status = "FAIL"
            description = (
                f"user_a (khong phai admin) goi thanh cong {endpoint.method} {endpoint.path} "
                f"(HTTP {resp.status_code})."
            )
        else:
            status = "NEEDS_REVIEW"
            description = f"HTTP {resp.status_code} khong ro rang cho endpoint chuc nang admin."

        return CheckResult(
            owasp_id=self.owasp_id,
            name=self.name,
            status=status,
            description=description,
            evidence=evidence,
        )
