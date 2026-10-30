from app.engine.zap.alerts import build_zap_alert, map_confidence_to_status


def test_high_confidence_maps_to_fail() -> None:
    assert map_confidence_to_status("High") == "FAIL"


def test_medium_confidence_maps_to_fail() -> None:
    assert map_confidence_to_status("Medium") == "FAIL"


def test_low_confidence_maps_to_needs_review() -> None:
    assert map_confidence_to_status("Low") == "NEEDS_REVIEW"


def test_false_positive_confidence_maps_to_needs_review() -> None:
    assert map_confidence_to_status("False Positive") == "NEEDS_REVIEW"


def test_build_zap_alert_masks_bearer_token_in_evidence() -> None:
    raw = {
        "alert": "SQL Injection",
        "risk": "High",
        "confidence": "High",
        "url": "http://target.local/users/1",
        "param": "id",
        "description": "desc",
        "solution": "fix it",
        "cweid": "89",
        "evidence": "Authorization: Bearer abc.def.ghi",
    }

    alert = build_zap_alert(raw)

    assert alert.status == "FAIL"
    assert "abc.def.ghi" not in alert.evidence
    assert "Bearer ***MASKED***" in alert.evidence
