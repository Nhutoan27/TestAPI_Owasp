"""Dieu phoi 1 lan ZAP scan: import spec OpenAPI -> active scan -> lay alert.

Cac ham goi API dong bo (blocking) cua zapv2. Active scan co the chay nhieu
phut va co the lam hong du lieu target, nen phai duoc goi tu background job
(runner, se xay o buoc 4), khong bao gio goi truc tiep trong request handler.
"""

import json
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

from app.core.config import Settings, get_settings
from app.core.security import mask_target_allowlist_check
from app.engine.zap.alerts import ZapAlert, build_zap_alert


class ScanTargetNotAllowedError(Exception):
    pass


def check_target_allowed(target_base_url: str, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    host = urlparse(target_base_url).hostname or ""
    if not mask_target_allowlist_check(host, settings.allowed_target_hosts_list):
        raise ScanTargetNotAllowedError(f"Target '{host}' khong nam trong allowlist cho phep scan.")


def import_openapi_spec(zap, raw_content: dict, target_base_url: str) -> object:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(raw_content, f)
        temp_path = f.name
    try:
        return zap.openapi.import_file(temp_path, target_base_url)
    finally:
        Path(temp_path).unlink(missing_ok=True)


def start_active_scan(zap, target_base_url: str) -> str:
    return zap.ascan.scan(target_base_url)


def wait_for_scan(zap, scan_id: str, poll_interval: float = 2.0, timeout: float = 600.0) -> None:
    elapsed = 0.0
    while int(zap.ascan.status(scan_id)) < 100:
        if elapsed >= timeout:
            raise TimeoutError(f"ZAP active scan {scan_id} chua xong sau {timeout}s")
        time.sleep(poll_interval)
        elapsed += poll_interval


def get_alerts(zap, target_base_url: str) -> list[ZapAlert]:
    raw_alerts = zap.core.alerts(baseurl=target_base_url)
    return [build_zap_alert(raw) for raw in raw_alerts]


def run_zap_scan(
    zap,
    target_base_url: str,
    raw_openapi_content: dict,
    settings: Settings | None = None,
) -> list[ZapAlert]:
    check_target_allowed(target_base_url, settings)

    import_openapi_spec(zap, raw_openapi_content, target_base_url)
    scan_id = start_active_scan(zap, target_base_url)
    wait_for_scan(zap, scan_id)
    return get_alerts(zap, target_base_url)
