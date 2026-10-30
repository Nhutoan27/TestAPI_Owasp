# TestAPI_Owasp

Công cụ kiểm thử bảo mật REST API theo **OWASP API Security Top 10 (2023)**.

Điều phối kiểm thử bằng FastAPI: OWASP ZAP quét lỗi cấu hình/injection, các custom
check tự viết (BOLA, BFLA) kiểm tra lỗi logic phân quyền, kết quả được đánh giá
thống nhất (PASS/FAIL/NEEDS_REVIEW/ERROR), lưu lịch sử để so sánh giữa các lần
scan, và AI hỗ trợ điều chỉnh severity (có kèm lý do).

Target chính: API của dự án **DC** (ASP.NET Core). Benchmark để đo hiệu quả:
**VAmPI** và **crAPI**.

Chi tiết quy ước code, kiến trúc và quy tắc an toàn: xem [CLAUDE.md](CLAUDE.md).

## Trạng thái hiện tại

| Bước lộ trình | Trạng thái |
|---|---|
| 1. FastAPI skeleton, DB, importer OpenAPI | Xong |
| 2. Auth profiles, check BOLA/BFLA | Xong |
| 3. Tích hợp ZAP | Xong (adapter độc lập, chưa có daemon ZAP thật để chạy demo) |
| 4. Evaluator, lịch sử scan, so sánh | Xong |
| 5. AI analyzer, báo cáo | Xong (đã test với LLM giả lập, chưa gọi provider thật) |
| 6. Đánh giá trên VAmPI/crAPI | Chưa chạy được — cần Docker (máy hiện tại không có) + ground truth xác nhận. Công cụ tính detection rate / false positive rate đã có sẵn ở [scripts/run_benchmark.py](scripts/run_benchmark.py). |

Toàn bộ logic nghiệp vụ (không cần Postgres/ZAP/LLM thật) đã có test tự động
chạy qua (`pytest`), bao gồm cả các test ghi DB thật trên Postgres.

## Tech stack

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.x (async), Alembic
- **Database:** PostgreSQL (asyncpg); bằng chứng request/response lưu dạng JSONB
- **Scanner:** OWASP ZAP (Docker), gọi qua `zapv2`, import spec bằng add-on OpenAPI
- **HTTP client:** `httpx` (async) — dùng cho custom check, auth token, và gọi LLM
- **AI:** LLM API tương thích OpenAI Chat Completions, output bắt buộc theo JSON schema
- **Test:** pytest, pytest-asyncio

## Chạy thử

```bash
cp .env.example .env            # sua DATABASE_URL va cac key can thiet
docker compose up -d            # postgres, zap
alembic upgrade head            # tao schema
uvicorn app.main:app --reload   # chay API tai http://localhost:8000
pytest                          # chay toan bo test (can DATABASE_URL tro toi Postgres thuc)
```

Target scan (API DC/VAmPI/crAPI) không nằm trong `docker-compose.yml` của repo
này — thêm theo hướng dẫn của từng dự án đó, và nhớ thêm hostname vào
`ALLOWED_TARGET_HOSTS` trong `.env`.

## Kiến trúc

```
app/
  api/routes/      projects.py (project, import spec, auth profile)
                   scans.py (trigger/xem scan, report, so sanh, AI assess)
  core/            config.py (Settings qua pydantic-settings), security.py (mask chung)
  db/              models.py, session.py, crud.py (projects/specs/auth-profiles), base.py
  schemas/         Pydantic request/response
  importers/       base.py (mo hinh Endpoint chung), openapi.py (parse JSON/YAML)
  auth/            token_provider.py (lay/lam moi token user A/B/admin)
  engine/
    runner.py       dieu phoi 1 scan run (custom check + ZAP)
    checks/          base.py (BaseCheck/CheckResult), bola.py, bfla.py
    zap/             client.py, alerts.py (map confidence->status), scanner.py
  evaluator/        severity.py (rule severity co so), persist.py (ghi DB)
  ai/               schema.py, client.py, analyzer.py (dieu chinh severity, co ly do)
  reports/          history.py, compare.py (so sanh 2 lan scan), export.py (bao cao),
                     benchmark.py (detection rate / false positive rate)
scripts/
  run_benchmark.py  CLI tinh so lieu benchmark tu 1 scan_run + file ground truth
benchmarks/
  ground_truth.example.json  dinh dang file ground truth (placeholder, chua phai du lieu thuc)
alembic/            migration (0001-0004: core tables -> auth_profiles -> evaluator tables -> ai_assessments)
tests/              test tung module + test end-to-end qua TestClient
```

## API chính

- `POST /projects` — tạo project (kiểm tra `target_base_url` nằm trong allowlist)
- `POST /projects/{id}/specs/openapi` — import OpenAPI spec (JSON hoặc YAML)
- `POST /projects/{id}/auth-profiles` — tạo auth profile (static token hoặc login_url)
- `POST /projects/{id}/scans` — trigger 1 scan (chạy nền qua `BackgroundTasks`, trả về ngay)
- `GET /projects/{id}/scans` — lịch sử scan của project
- `GET /scans/{id}` — trạng thái + tóm tắt số lượng PASS/FAIL/NEEDS_REVIEW/ERROR
- `GET /scans/{id}/report` — báo cáo chi tiết (finding, severity gốc/AI)
- `GET /scans/compare?old=&new=` — so sánh 2 lần scan (NEW/RESOLVED/REGRESSED/STILL_FAILING)
- `POST /scans/{id}/ai-assess` — chạy AI điều chỉnh severity cho các finding trong scan run

## Biến môi trường

Xem [.env.example](.env.example): `DATABASE_URL`, `ALLOWED_TARGET_HOSTS`,
`ZAP_HOST`/`ZAP_PORT`/`ZAP_API_KEY`, `OPENAI_API_KEY`/`OPENAI_BASE_URL`/`OPENAI_MODEL`.

## Giới hạn hiện tại

- Chưa chạy được với ZAP daemon thật hoặc LLM provider thật trong môi trường phát
  triển này — các phần đó được test bằng client/transport giả lập (`httpx.MockTransport`,
  fake ZAP client) theo đúng interface thật.
- Bước 6 (đánh giá VAmPI/crAPI) cần Docker + ground truth do người dùng xác nhận
  từ README của từng benchmark — không tự bịa số liệu.
- ZAP alert chỉ phân loại `OTHER` (injection) hoặc `API8:2023` (còn lại) theo từ
  khoá trong tên alert — heuristic đơn giản.
- API6, API7, API10 ngoài phạm vi (đánh dấu `NEEDS_REVIEW` theo CLAUDE.md), chưa triển khai.
