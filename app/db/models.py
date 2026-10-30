"""Model cho cac bang duoc dung tu buoc 1 (skeleton + importer), buoc 2 (auth
profiles) va buoc 4 (evaluator + lich su scan).

Bang `ai_assessments` se duoc them khi trien khai buoc 5 (AI analyzer), tranh
tao schema truoc khi co logic dung den.
"""

from datetime import datetime, timezone

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    target_base_url: Mapped[str] = mapped_column(String(2048))
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    api_specs: Mapped[list["ApiSpec"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class ApiSpec(Base):
    __tablename__ = "api_specs"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    source_type: Mapped[str] = mapped_column(String(32))  # "openapi" | "postman"
    version: Mapped[str] = mapped_column(String(64), default="")
    raw_content: Mapped[dict] = mapped_column(JSON)
    imported_at: Mapped[datetime] = mapped_column(default=_utcnow)

    project: Mapped["Project"] = relationship(back_populates="api_specs")
    endpoints: Mapped[list["Endpoint"]] = relationship(back_populates="api_spec", cascade="all, delete-orphan")


class Endpoint(Base):
    __tablename__ = "endpoints"

    id: Mapped[int] = mapped_column(primary_key=True)
    api_spec_id: Mapped[int] = mapped_column(ForeignKey("api_specs.id"))
    method: Mapped[str] = mapped_column(String(16))
    path: Mapped[str] = mapped_column(String(2048))
    operation_id: Mapped[str] = mapped_column(String(255), default="")
    summary: Mapped[str] = mapped_column(String(1024), default="")
    tags: Mapped[list] = mapped_column(JSON, default=list)

    api_spec: Mapped["ApiSpec"] = relationship(back_populates="endpoints")
    parameters: Mapped[list["Parameter"]] = relationship(back_populates="endpoint", cascade="all, delete-orphan")


class Parameter(Base):
    __tablename__ = "parameters"

    id: Mapped[int] = mapped_column(primary_key=True)
    endpoint_id: Mapped[int] = mapped_column(ForeignKey("endpoints.id"))
    name: Mapped[str] = mapped_column(String(255))
    location: Mapped[str] = mapped_column(String(16))  # path | query | header | cookie | body
    required: Mapped[bool] = mapped_column(default=False)
    schema_json: Mapped[dict] = mapped_column(JSON, default=dict)

    endpoint: Mapped["Endpoint"] = relationship(back_populates="parameters")


class AuthProfile(Base):
    """Auth profile de lay/lam moi token cho user A / user B / admin (dung cho check BOLA/BFLA)."""

    __tablename__ = "auth_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32))  # user_a | user_b | admin
    # Co login_url -> dang nhap de lay token moi; khong co -> dung static_token truc tiep.
    login_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    credentials: Mapped[dict] = mapped_column(JSON, default=dict)
    token_path: Mapped[str] = mapped_column(String(255), default="access_token")
    static_token: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)


class TestCase(Base):
    """1 to hop (endpoint, check) can test. endpoint_id co the NULL voi ket qua tu ZAP
    o muc target (khong gan duoc vao 1 endpoint cu the)."""

    __tablename__ = "test_cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    endpoint_id: Mapped[int | None] = mapped_column(ForeignKey("endpoints.id"), nullable=True)
    owasp_id: Mapped[str] = mapped_column(String(32))
    check_name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    endpoint: Mapped["Endpoint | None"] = relationship()


class ScanRun(Base):
    __tablename__ = "scan_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|running|completed|failed
    started_at: Mapped[datetime] = mapped_column(default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)

    test_results: Mapped[list["TestResult"]] = relationship(
        back_populates="scan_run", cascade="all, delete-orphan"
    )


class TestResult(Base):
    __tablename__ = "test_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_run_id: Mapped[int] = mapped_column(ForeignKey("scan_runs.id", ondelete="CASCADE"))
    test_case_id: Mapped[int] = mapped_column(ForeignKey("test_cases.id"))
    status: Mapped[str] = mapped_column(String(16))  # PASS|FAIL|NEEDS_REVIEW|ERROR
    severity_base: Mapped[str | None] = mapped_column(String(16), nullable=True)
    severity_ai: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    scan_run: Mapped["ScanRun"] = relationship(back_populates="test_results")
    evidence: Mapped["Evidence | None"] = relationship(
        back_populates="test_result", cascade="all, delete-orphan", uselist=False
    )
    finding: Mapped["Finding | None"] = relationship(
        back_populates="test_result", cascade="all, delete-orphan", uselist=False
    )


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    test_result_id: Mapped[int] = mapped_column(
        ForeignKey("test_results.id", ondelete="CASCADE"), unique=True
    )
    data: Mapped[dict] = mapped_column(JSON)  # request/response/auth_profile_used, da mask

    test_result: Mapped["TestResult"] = relationship(back_populates="evidence")


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    test_result_id: Mapped[int] = mapped_column(
        ForeignKey("test_results.id", ondelete="CASCADE"), unique=True
    )
    owasp_id: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(512))
    description: Mapped[str] = mapped_column(String(4096))
    severity: Mapped[str] = mapped_column(String(16))

    test_result: Mapped["TestResult"] = relationship(back_populates="finding")
    ai_assessments: Mapped[list["AiAssessment"]] = relationship(
        back_populates="finding", cascade="all, delete-orphan"
    )


class AiAssessment(Base):
    """AI chi DIEU CHINH severity co so (luu ca 2 ben) va phai kem ly do - khong tu quyet
    severity khi chua co gia tri co so (Finding.severity luon co san tu evaluator)."""

    __tablename__ = "ai_assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    finding_id: Mapped[int] = mapped_column(ForeignKey("findings.id", ondelete="CASCADE"))
    severity_original: Mapped[str] = mapped_column(String(16))
    severity_suggested: Mapped[str] = mapped_column(String(16))
    reasoning: Mapped[str] = mapped_column(String(4096))
    raw_output: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    finding: Mapped["Finding"] = relationship(back_populates="ai_assessments")
