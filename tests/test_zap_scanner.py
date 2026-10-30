import itertools

import pytest

from app.engine.zap.scanner import (
    ScanTargetNotAllowedError,
    check_target_allowed,
    run_zap_scan,
    wait_for_scan,
)


class _FakeOpenApi:
    def __init__(self) -> None:
        self.imported_target: str | None = None

    def import_file(self, file: str, target: str) -> str:
        self.imported_target = target
        return "OK"


class _FakeAscan:
    def __init__(self, statuses) -> None:
        self._statuses = iter(statuses)
        self.scanned_target: str | None = None

    def scan(self, target: str) -> str:
        self.scanned_target = target
        return "scan-1"

    def status(self, scan_id: str) -> int:
        return next(self._statuses)


class _FakeCore:
    def __init__(self, alerts: list[dict]) -> None:
        self._alerts = alerts
        self.queried_baseurl: str | None = None

    def alerts(self, baseurl: str | None = None) -> list[dict]:
        self.queried_baseurl = baseurl
        return self._alerts


class _FakeZap:
    def __init__(self, statuses, alerts: list[dict]) -> None:
        self.openapi = _FakeOpenApi()
        self.ascan = _FakeAscan(statuses)
        self.core = _FakeCore(alerts)


def test_check_target_allowed_rejects_target_outside_allowlist() -> None:
    with pytest.raises(ScanTargetNotAllowedError):
        check_target_allowed("http://evil.example.com")


def test_check_target_allowed_accepts_localhost() -> None:
    check_target_allowed("http://localhost:5000")  # khong raise


def test_run_zap_scan_imports_spec_scans_and_maps_alerts() -> None:
    raw_alert = {"alert": "XSS", "risk": "Medium", "confidence": "High", "url": "http://localhost:5000/x"}
    zap = _FakeZap(statuses=[100], alerts=[raw_alert])

    result = run_zap_scan(zap, "http://localhost:5000", {"openapi": "3.0.0", "paths": {}})

    assert len(result) == 1
    assert result[0].status == "FAIL"
    assert zap.openapi.imported_target == "http://localhost:5000"
    assert zap.ascan.scanned_target == "http://localhost:5000"
    assert zap.core.queried_baseurl == "http://localhost:5000"


def test_run_zap_scan_rejects_target_outside_allowlist_without_touching_zap() -> None:
    zap = _FakeZap(statuses=[100], alerts=[])

    with pytest.raises(ScanTargetNotAllowedError):
        run_zap_scan(zap, "http://evil.example.com", {"openapi": "3.0.0", "paths": {}})

    assert zap.openapi.imported_target is None
    assert zap.ascan.scanned_target is None


def test_wait_for_scan_times_out_when_scan_never_completes() -> None:
    zap = _FakeZap(statuses=itertools.repeat(0), alerts=[])

    with pytest.raises(TimeoutError):
        wait_for_scan(zap, "scan-1", poll_interval=0.01, timeout=0.03)
