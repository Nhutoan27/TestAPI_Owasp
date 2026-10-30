# CLAUDE.md

Hướng dẫn cho Claude khi làm việc trong repo này.

## Tổng quan dự án

Công cụ kiểm thử bảo mật REST API theo **OWASP API Security Top 10 (2023)**.

Công cụ có các chức năng chính:
- Import API từ OpenAPI/Swagger hoặc Postman.
- Điều phối kiểm thử bằng FastAPI, trong đó ZAP quét lỗi cấu hình và injection, còn các check Python tự viết kiểm tra lỗi logic phân quyền.
- Lưu kết quả kèm bằng chứng.
- Dùng AI để hỗ trợ đánh giá rủi ro.

Target chính là API của dự án **DC** (ASP.NET Core). Benchmark để đo hiệu quả tool là **VAmPI** và **crAPI**, vì đã biết trước danh sách lỗ hổng.

Giá trị cốt lõi của tool **không nằm ở việc chạy ZAP**. Nó nằm ở ba phần:
1. Custom checks cho BOLA, BFLA, BOPLA.
2. Lớp đánh giá kết quả thống nhất.
3. Quản lý lịch sử và so sánh giữa các lần scan.

Khi phải đánh đổi về thời gian hoặc độ phức tạp, ưu tiên ba phần này.

## Tech stack

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy 2.x (async), Alembic
- **Database:** PostgreSQL; bằng chứng request/response lưu dạng JSONB
- **Scanner:** OWASP ZAP chạy bằng Docker, gọi qua client `zapv2`, import spec bằng add-on OpenAPI
- **HTTP client cho custom checks:** `httpx` (async)
- **Background jobs:** scan chạy nền, không chạy đồng bộ trong request HTTP
- **AI:** LLM API, output bắt buộc theo JSON schema
- **Test:** pytest, pytest-asyncio

## Kiến trúc

```
app/
  api/            # FastAPI routers (chỉ nhận/trả request, không chứa logic)
  core/           # config, logging, security helpers (masking)
  db/             # models, session, migrations
  schemas/        # Pydantic schemas
  importers/      # openapi.py, postman.py → chuẩn hóa về mô hình Endpoint chung
  auth/           # auth profiles: lấy và làm mới token cho user A / user B / admin
  engine/
    runner.py     # điều phối một scan run
    zap/          # adapter ZAP
    checks/       # custom checks dạng plugin, mỗi file một check
  evaluator/      # gán PASS/FAIL/NEEDS_REVIEW/ERROR và severity cơ sở
  ai/             # gọi LLM, prompt, kiểm tra output schema
  reports/        # xuất báo cáo, so sánh các lần chạy
tests/
```

Luồng xử lý: Importer → Auth Manager → Test Engine (ZAP và Custom Checks) → Evaluator → AI Analyzer → Storage/Report.

### Các bảng chính

`projects`, `api_specs`, `endpoints`, `parameters`, `auth_profiles`, `test_cases`, `scan_runs`, `test_results`, `evidence`, `findings`, `ai_assessments`

## Quy ước

### Custom checks

- Mỗi check là một class kế thừa `BaseCheck` và khai báo `owasp_id` (ví dụ `API1:2023`), `name` và `applies_to(endpoint)`.
- Hàm `run()` trả về `CheckResult`, không tự ghi vào DB.
- Thêm một loại kiểm thử mới chỉ cần thêm một file trong `engine/checks/`, không sửa runner.
- Mỗi check phải lưu đủ bằng chứng để người khác tái hiện được: request, response, auth profile đã dùng.

### Trạng thái kết quả

| Trạng thái | Ý nghĩa |
|---|---|
| `PASS` | Đã test và không phát hiện vấn đề. Trong báo cáo phải ghi là "không phát hiện", không ghi là "an toàn". |
| `FAIL` | Có bằng chứng rõ ràng về lỗ hổng. |
| `NEEDS_REVIEW` | Có dấu hiệu nhưng chưa chắc chắn. |
| `ERROR` | Không thực hiện được test, ví dụ timeout, lỗi auth hoặc endpoint không phản hồi. |

Cách map alert của ZAP:
- Confidence High hoặc Medium → `FAIL`
- Confidence Low hoặc False Positive → `NEEDS_REVIEW`
- Không có alert → `PASS`

### Severity

- Severity cơ sở do rule xác định (Low, Medium, High, Critical).
- AI chỉ được **điều chỉnh** severity và phải kèm lý do. Không bao giờ để AI tự quyết định severity khi chưa có giá trị cơ sở.
- Luôn lưu cả severity gốc lẫn severity do AI đề xuất.

### Phạm vi OWASP

- **Làm sâu:** API1 (BOLA), API2 (Authentication), API3 (BOPLA và mass assignment), API5 (BFLA), API8 (Misconfiguration, chủ yếu dùng ZAP), API9 (Inventory)
- **Làm cơ bản:** API4 (rate limit, page size)
- **Đánh dấu `NEEDS_REVIEW` hoặc ngoài phạm vi:** API6, API7, API10
- **Injection** (SQLi, XSS do ZAP phát hiện): không còn là mục riêng trong bản 2023, gom vào nhóm `OTHER`

### Code style

- Có type hints đầy đủ. Dùng async cho I/O.
- Router chỉ gọi service, không chứa logic nghiệp vụ.
- Lấy config từ biến môi trường qua `pydantic-settings`, không hardcode URL, token hay API key.
- Comment và docstring viết bằng tiếng Việt hoặc tiếng Anh đều được, nhưng trong một file phải thống nhất một ngôn ngữ.

## Quy tắc an toàn (bắt buộc)

- **Chỉ scan các target nằm trong allowlist** cấu hình sẵn: localhost, container của DC, VAmPI, crAPI. Từ chối mọi target ngoài danh sách này.
- Active scan có thể làm hỏng dữ liệu. Target phải chạy trong Docker với dữ liệu seed riêng và có thể reset được.
- **Che (mask) token, mật khẩu, cookie và PII** trước khi lưu log hoặc gửi bằng chứng lên LLM. Dùng hàm masking chung trong `core/`.
- Không commit file `.env`, token hoặc dữ liệu scan thật.

## Lệnh thường dùng

```bash
docker compose up -d                 # postgres, zap, target (DC/VAmPI)
uvicorn app.main:app --reload        # chạy API
alembic upgrade head                 # migrate DB
pytest                               # chạy test
```

Hãy cập nhật mục này khi lệnh thực tế thay đổi.

## Lộ trình

1. FastAPI skeleton, DB và importer (OpenAPI trước, Postman sau)
2. Auth profiles và check BOLA/BFLA, vì đây là phần cốt lõi và khó nhất
3. Tích hợp ZAP
4. Evaluator, lịch sử scan và so sánh các lần chạy
5. AI analyzer và báo cáo
6. Đánh giá trên VAmPI/crAPI: tỉ lệ phát hiện và tỉ lệ báo sai

## Lưu ý khi Claude làm việc

- Trước khi thêm dependency mới, hỏi trước.
- Khi viết check mới, viết kèm test với một endpoint giả lập có lỗi và một endpoint không có lỗi.
- Không tự ý mở rộng phạm vi sang API6, API7, API10 khi chưa được yêu cầu.
