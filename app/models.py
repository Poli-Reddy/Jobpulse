from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

JSON_DOCUMENT = JSON().with_variant(JSONB, "postgresql")


class RawJob(Base):
    __tablename__ = "raw_jobs"
    __table_args__ = (
        UniqueConstraint("source", "source_job_id", "payload_hash", name="uq_raw_job_payload"),
        Index("ix_raw_jobs_source_job", "source", "source_job_id"),
        {"schema": "raw"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_job_id: Mapped[str] = mapped_column(String(255), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class RawSourceRun(Base):
    __tablename__ = "raw_source_runs"
    __table_args__ = (
        Index("ix_raw_source_runs_source_started", "source", "started_at"),
        {"schema": "raw"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pipeline_run_id: Mapped[int] = mapped_column(
        ForeignKey("monitoring.pipeline_runs.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    records_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer)


class StgCompany(Base):
    __tablename__ = "stg_companies"
    __table_args__ = (UniqueConstraint("normalized_name", name="uq_stg_companies_normalized"), {"schema": "staging"})

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StgLocation(Base):
    __tablename__ = "stg_locations"
    __table_args__ = (
        UniqueConstraint("normalized_key", name="uq_stg_locations_normalized"),
        Index("ix_stg_locations_remote", "remote"),
        {"schema": "staging"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    raw_location: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_location: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str | None] = mapped_column(String(120))
    country: Mapped[str | None] = mapped_column(String(120))
    remote: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    normalized_key: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class StgJob(Base):
    __tablename__ = "stg_jobs"
    __table_args__ = (
        UniqueConstraint("source", "source_job_id", name="uq_stg_jobs_source_id"),
        CheckConstraint(
            "status IN ('NEW', 'ACTIVE', 'UPDATED', 'CLOSED', 'REACTIVATED')",
            name="ck_stg_jobs_status",
        ),
        CheckConstraint(
            "salary_min IS NULL OR salary_min >= 0", name="ck_stg_jobs_salary_min_nonnegative"
        ),
        CheckConstraint(
            "salary_max IS NULL OR salary_max >= 0", name="ck_stg_jobs_salary_max_nonnegative"
        ),
        CheckConstraint(
            "salary_min IS NULL OR salary_max IS NULL OR salary_max >= salary_min",
            name="ck_stg_jobs_salary_order",
        ),
        Index("ix_stg_jobs_status", "status"),
        Index("ix_stg_jobs_published", "published_at"),
        Index("ix_stg_jobs_company", "company_id"),
        Index("ix_stg_jobs_location", "location_id"),
        {"schema": "staging"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_job_id: Mapped[str] = mapped_column(String(255), nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("staging.stg_companies.id"), nullable=False)
    location_id: Mapped[int] = mapped_column(ForeignKey("staging.stg_locations.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    job_url: Mapped[str] = mapped_column(Text, nullable=False)
    employment_type: Mapped[str | None] = mapped_column(String(100))
    level: Mapped[str | None] = mapped_column(String(100))
    salary_min: Mapped[float | None] = mapped_column(Numeric(14, 2))
    salary_max: Mapped[float | None] = mapped_column(Numeric(14, 2))
    salary_currency: Mapped[str | None] = mapped_column(String(10))
    salary_period: Mapped[str | None] = mapped_column(String(30))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="NEW")
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class StgSkill(Base):
    __tablename__ = "stg_skills"
    __table_args__ = (UniqueConstraint("name", name="uq_stg_skills_name"), {"schema": "staging"})

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str | None] = mapped_column(String(80))


class StgJobSkill(Base):
    __tablename__ = "stg_job_skills"
    __table_args__ = (
        Index("ix_stg_job_skills_skill_job", "skill_id", "job_id"),
        {"schema": "staging"},
    )

    job_id: Mapped[int] = mapped_column(
        ForeignKey("staging.stg_jobs.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("staging.stg_skills.id", ondelete="CASCADE"), primary_key=True
    )


class StgJobHistory(Base):
    __tablename__ = "stg_job_history"
    __table_args__ = (
        Index("ix_stg_job_history_job_time", "job_id", "occurred_at"),
        {"schema": "staging"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("staging.stg_jobs.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('RUNNING', 'SUCCESS', 'PARTIAL_SUCCESS', 'FAILED')",
            name="ck_pipeline_runs_status",
        ),
        Index("ix_pipeline_runs_started", "started_at"),
        {"schema": "monitoring"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pipeline_name: Mapped[str] = mapped_column(String(100), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="RUNNING")
    records_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sources_succeeded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sources_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)


class DataQualityResult(Base):
    __tablename__ = "data_quality_results"
    __table_args__ = (
        Index("ix_data_quality_run_source", "pipeline_run_id", "source"),
        {"schema": "monitoring"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pipeline_run_id: Mapped[int] = mapped_column(
        ForeignKey("monitoring.pipeline_runs.id", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_job_id: Mapped[str | None] = mapped_column(String(255))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON_DOCUMENT, nullable=False)


class SourceStatus(Base):
    __tablename__ = "source_status"
    __table_args__ = (
        UniqueConstraint("source", name="uq_source_status_source"),
        Index("ix_source_status_last_run", "last_run_at"),
        {"schema": "monitoring"},
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="NEVER_RUN")
    records_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_inserted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    consecutive_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
