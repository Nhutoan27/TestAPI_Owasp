"""CLI: tinh detection rate / false positive rate cho 1 scan_run da chay thuc te,
so voi 1 file ground truth (danh sach lo hong da biet truoc cua VAmPI/crAPI).

Dieu kien truoc khi dung duoc script nay (chua co trong moi truong phat trien nay):
  1. Docker dang chay, VAmPI/crAPI da duoc them vao docker-compose.yml va dang chay.
  2. Da import OpenAPI spec cua VAmPI/crAPI va chay scan thuc qua POST /projects/{id}/scans.
  3. Co 1 file ground truth JSON ban tu lap, doi chieu tu README cua VAmPI/crAPI
     (xem benchmarks/ground_truth.example.json de biet dinh dang - file example
     CHI la placeholder, khong phai danh sach lo hong thuc).

Vi du chay:
    python scripts/run_benchmark.py --scan-run-id 12 --ground-truth benchmarks/vampi_ground_truth.json
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.reports.benchmark import (  # noqa: E402
    GroundTruthItem,
    ReportedFinding,
    evaluate_against_ground_truth,
)
from app.reports.export import generate_scan_report  # noqa: E402


async def _run(scan_run_id: int, ground_truth_path: Path) -> dict:
    ground_truth_data = json.loads(ground_truth_path.read_text(encoding="utf-8"))
    ground_truth = [GroundTruthItem(item["endpoint_path"], item["owasp_id"]) for item in ground_truth_data]

    engine = create_async_engine(get_settings().database_url)
    try:
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory() as db:
            report = await generate_scan_report(db, scan_run_id)
    finally:
        await engine.dispose()

    findings = [ReportedFinding(entry.endpoint_path or "", entry.owasp_id) for entry in report.findings]
    result = evaluate_against_ground_truth(findings, ground_truth)

    return {
        "scan_run_id": scan_run_id,
        "true_positives": result.true_positives,
        "false_negatives": result.false_negatives,
        "false_positives": result.false_positives,
        "total_known_vulnerabilities": result.total_known_vulnerabilities,
        "total_findings": result.total_findings,
        "detection_rate": round(result.detection_rate, 4),
        "false_positive_rate": round(result.false_positive_rate, 4),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tinh detection rate / false positive rate cho 1 scan_run")
    parser.add_argument("--scan-run-id", type=int, required=True)
    parser.add_argument("--ground-truth", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(asyncio.run(_run(args.scan_run_id, args.ground_truth)), indent=2, ensure_ascii=False))
