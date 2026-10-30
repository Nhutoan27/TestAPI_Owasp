"""Tinh ti le phat hien (detection rate) va ti le bao sai (false positive rate)
cho 1 lan scan, dua tren ground truth da biet truoc - dung de danh gia tren
VAmPI/crAPI theo buoc 6 cua lo trinh.

Module nay CHI la may tinh so lieu thuan (khong goi DB, khong biet gi ve
VAmPI/crAPI). Ground truth (danh sach lo hong thuc su da biet) phai duoc nguoi
dung cung cap sau khi da chay scan thuc te tren container VAmPI/crAPI dang
chay (xem README cua tung benchmark de lay danh sach lo hong da cong bo) -
module nay khong tu suy ra hay gia dinh ground truth.

shortcut: so khop chi theo (endpoint_path, owasp_id), khong theo HTTP method -
ZAP alert (ZapAlert) khong luu method nen khong the doi xu nhat quan; VAmPI/
crAPI hiem khi co 2 method khac nhau cung bi loi tren cung 1 path nen chap
nhan duoc. Nang cap: them method vao ZapAlert/FindingReportEntry neu can phan
biet chinh xac hon.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class GroundTruthItem:
    endpoint_path: str
    owasp_id: str


@dataclass
class ReportedFinding:
    endpoint_path: str
    owasp_id: str


@dataclass
class BenchmarkResult:
    true_positives: int
    false_negatives: int
    false_positives: int
    total_known_vulnerabilities: int
    total_findings: int
    detection_rate: float  # true_positives / total_known_vulnerabilities
    false_positive_rate: float  # false_positives / total_findings


def _key(endpoint_path: str, owasp_id: str) -> tuple[str, str]:
    return (endpoint_path, owasp_id)


def evaluate_against_ground_truth(
    findings: list[ReportedFinding], ground_truth: list[GroundTruthItem]
) -> BenchmarkResult:
    found_keys = {_key(f.endpoint_path, f.owasp_id) for f in findings}
    truth_keys = {_key(g.endpoint_path, g.owasp_id) for g in ground_truth}

    true_positives = len(found_keys & truth_keys)
    false_negatives = len(truth_keys - found_keys)
    false_positives = len(found_keys - truth_keys)

    total_known = len(truth_keys)
    total_findings = len(found_keys)

    return BenchmarkResult(
        true_positives=true_positives,
        false_negatives=false_negatives,
        false_positives=false_positives,
        total_known_vulnerabilities=total_known,
        total_findings=total_findings,
        detection_rate=(true_positives / total_known) if total_known else 0.0,
        false_positive_rate=(false_positives / total_findings) if total_findings else 0.0,
    )
