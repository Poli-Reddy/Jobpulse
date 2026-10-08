import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.connectors import SourceRecord, enabled_connectors
from app.models import (
    DataQualityResult,
    PipelineRun,
    RawJob,
    RawSourceRun,
    SourceStatus,
    StgCompany,
    StgJob,
    StgJobHistory,
    StgJobSkill,
    StgLocation,
    StgSkill,
)
from app.normalization import SKILL_CATEGORIES, norm_key, normalize_location
from app.schemas import NormalizedJob
from app.storage import payload_hash

log = logging.getLogger(__name__)

METRIC_KEYS = (
    "records_received",
    "records_inserted",
    "records_updated",
    "records_rejected",
    "duplicates",
)


def _content_hash(job: NormalizedJob) -> str:
    content = {
        "title": job.title,
        "company_name": norm_key(job.company_name),
        "company_domain": job.company_domain,
        "location": normalize_location(job.location),
        "remote": job.remote,
        "description": job.description,
        "job_url": str(job.job_url),
        "employment_type": job.employment_type,
        "level": job.level,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "salary_currency": job.salary_currency,
        "salary_period": job.salary_period,
        "published_at": job.published_at.isoformat() if job.published_at else None,
        "skills": sorted(job.skills, key=str.casefold),
    }
    return hashlib.sha256(
        json.dumps(content, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _get_or_create_company(db: Session, name: str, domain: str | None, now: datetime):
    key = norm_key(name)
    company = db.scalar(select(StgCompany).where(StgCompany.normalized_name == key))
    if company is None:
        company = StgCompany(
            name=name,
            normalized_name=key,
            domain=domain,
            created_at=now,
            updated_at=now,
        )
        db.add(company)
        db.flush()
    elif domain and not company.domain:
        company.domain = domain
        company.updated_at = now
    return company


def _get_or_create_location(db: Session, raw: str, remote: bool, now: datetime):
    normalized = normalize_location(raw)
    key = f"{norm_key(normalized)}|remote={str(remote).lower()}"
    location = db.scalar(select(StgLocation).where(StgLocation.normalized_key == key))
    if location is None:
        parts = [part.strip() for part in normalized.replace("|", ",").split(",") if part.strip()]
        location = StgLocation(
            raw_location=raw,
            normalized_location=normalized,
            city=parts[0] if parts else None,
            country=parts[-1] if len(parts) > 1 else None,
            remote=remote,
            normalized_key=key,
            created_at=now,
        )
        db.add(location)
        db.flush()
    return location


def _get_or_create_skill(db: Session, name: str):
    skill = db.scalar(select(StgSkill).where(StgSkill.name == name))
    if skill is None:
        skill = StgSkill(name=name, category=SKILL_CATEGORIES.get(name))
        db.add(skill)
        db.flush()
    return skill


def _source_job_id(record: SourceRecord, source: str, digest: str) -> str:
    if record.job is not None:
        return record.job.source_job_id
    try:
        from app.normalization import deterministic_job_id

        return deterministic_job_id(source, record.payload)
    except ValueError:
        return f"invalid:{digest}"


def _record_snapshot(job: NormalizedJob) -> dict[str, Any]:
    return job.model_dump(mode="json")


def _append_history(
    db: Session, job: StgJob, event: str, now: datetime, snapshot: dict[str, Any]
) -> None:
    db.add(
        StgJobHistory(
            job_id=job.id,
            event_type=event,
            occurred_at=now,
            content_hash=job.content_hash,
            snapshot=snapshot,
        )
    )


def _process_record(
    db: Session, record: SourceRecord, source: str, pipeline_run_id: int, now: datetime
) -> str:
    digest = payload_hash(record.payload)
    source_job_id = _source_job_id(record, source, digest)
    if record.job is None:
        if db.scalar(
            select(RawJob.id).where(
                RawJob.source == source,
                RawJob.source_job_id == source_job_id,
                RawJob.payload_hash == digest,
            )
        ) is None:
            db.add(
                RawJob(
                    source=source,
                    source_job_id=source_job_id,
                    fetched_at=now,
                    payload=record.payload,
                    payload_hash=digest,
                )
            )
        db.add(
            DataQualityResult(
                pipeline_run_id=pipeline_run_id,
                source=source,
                source_job_id=source_job_id,
                recorded_at=now,
                reason=record.error or "normalization failed",
                payload=record.payload,
            )
        )
        return "rejected"

    job = record.job
    existing_raw = db.scalar(
        select(RawJob.id).where(
            RawJob.source == source,
            RawJob.source_job_id == source_job_id,
            RawJob.payload_hash == digest,
        )
    )
    if existing_raw is None:
        db.add(
            RawJob(
                source=source,
                source_job_id=source_job_id,
                fetched_at=now,
                payload=record.payload,
                payload_hash=digest,
            )
        )

    company = _get_or_create_company(db, job.company_name, job.company_domain, now)
    location = _get_or_create_location(db, job.location, job.remote, now)
    existing = db.scalar(
        select(StgJob).where(
            StgJob.source == source, StgJob.source_job_id == source_job_id
        )
    )
    new_hash = _content_hash(job)
    snapshot = _record_snapshot(job)
    explicitly_closed = str(record.payload.get("status") or "").casefold() == "closed"

    if existing is None:
        existing = StgJob(
            source=source,
            source_job_id=source_job_id,
            company_id=company.id,
            location_id=location.id,
            title=job.title,
            description=job.description,
            job_url=str(job.job_url),
            employment_type=job.employment_type,
            level=job.level,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            salary_currency=job.salary_currency,
            salary_period=job.salary_period,
            published_at=job.published_at,
            first_seen_at=now,
            last_seen_at=now,
            updated_at=now,
            status="CLOSED" if explicitly_closed else "NEW",
            content_hash=new_hash,
        )
        db.add(existing)
        db.flush()
        event = "CLOSED" if explicitly_closed else "NEW"
        result = "inserted"
    else:
        prior_status = existing.status
        existing.last_seen_at = now
        if explicitly_closed and prior_status != "CLOSED":
            event = "CLOSED"
            result = "updated"
        elif explicitly_closed:
            event = None
            result = "duplicate"
        elif prior_status == "CLOSED":
            event = "REACTIVATED"
            result = "updated"
        elif existing.content_hash != new_hash:
            event = "UPDATED"
            result = "updated"
        elif prior_status in {"NEW", "UPDATED", "REACTIVATED"}:
            event = "ACTIVE"
            result = "duplicate"
        else:
            event = None
            result = "duplicate"

        if event in {"UPDATED", "REACTIVATED", "CLOSED"}:
            existing.company_id = company.id
            existing.location_id = location.id
            existing.title = job.title
            existing.description = job.description
            existing.job_url = str(job.job_url)
            existing.employment_type = job.employment_type
            existing.level = job.level
            existing.salary_min = job.salary_min
            existing.salary_max = job.salary_max
            existing.salary_currency = job.salary_currency
            existing.salary_period = job.salary_period
            existing.published_at = job.published_at
            existing.updated_at = now
            existing.content_hash = new_hash
        if event is not None:
            existing.status = "ACTIVE" if event == "ACTIVE" else event

    skill_ids = set()
    for skill_name in job.skills:
        skill = _get_or_create_skill(db, skill_name)
        skill_ids.add(skill.id)
    existing_skill_ids = set(
        db.scalars(select(StgJobSkill.skill_id).where(StgJobSkill.job_id == existing.id))
    )
    if existing_skill_ids - skill_ids:
        db.execute(
            delete(StgJobSkill).where(
                StgJobSkill.job_id == existing.id,
                StgJobSkill.skill_id.in_(existing_skill_ids - skill_ids),
            )
        )
    for skill_id in skill_ids - existing_skill_ids:
        db.add(StgJobSkill(job_id=existing.id, skill_id=skill_id))

    if event is not None:
        _append_history(db, existing, event, now, snapshot)
    if existing_raw is not None and result == "duplicate":
        return "duplicate"
    return result


def _upsert_source_status(
    db: Session, source: str, status: str, now: datetime, metrics: dict[str, int], error: str | None
) -> None:
    row = db.scalar(select(SourceStatus).where(SourceStatus.source == source))
    if row is None:
        row = SourceStatus(source=source, status=status, consecutive_failures=0)
        db.add(row)
    row.last_run_at = now
    row.status = status
    for key in METRIC_KEYS:
        setattr(row, key, metrics[key])
    if status == "SUCCESS":
        row.last_success_at = now
        row.consecutive_failures = 0
        row.last_error = None
    else:
        row.last_failure_at = now
        row.consecutive_failures += 1
        row.last_error = error[:2000] if error else "source failed"


def process_source(
    db: Session, connector, pipeline_run_id: int
) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    started_clock = time.monotonic()
    metrics = {key: 0 for key in METRIC_KEYS}
    records: list[SourceRecord] = []
    error = None
    try:
        records = connector.fetch()
        metrics["records_received"] = len(records)
        for record in records:
            now = datetime.now(timezone.utc)
            try:
                with db.begin_nested():
                    result = _process_record(db, record, connector.name, pipeline_run_id, now)
                if result == "inserted":
                    metrics["records_inserted"] += 1
                elif result == "updated":
                    metrics["records_updated"] += 1
                elif result == "duplicate":
                    metrics["duplicates"] += 1
                else:
                    metrics["records_rejected"] += 1
                    log.warning(
                        "Rejected source record: source=%s source_job_id=%s reason=%s",
                        connector.name,
                        record.job.source_job_id if record.job is not None else "invalid",
                        record.error or "normalization failed",
                    )
            except Exception as exc:
                metrics["records_rejected"] += 1
                digest = payload_hash(record.payload)
                source_job_id = _source_job_id(record, connector.name, digest)
                log.exception(
                    "Record processing failed: source=%s source_job_id=%s",
                    connector.name,
                    source_job_id,
                )
                db.add(
                    DataQualityResult(
                        pipeline_run_id=pipeline_run_id,
                        source=connector.name,
                        source_job_id=source_job_id,
                        recorded_at=now,
                        reason=f"database or record processing error: {str(exc)[:900]}",
                        payload=record.payload,
                    )
                )
                if db.scalar(
                    select(RawJob.id).where(
                        RawJob.source == connector.name,
                        RawJob.source_job_id == source_job_id,
                        RawJob.payload_hash == digest,
                    )
                ) is None:
                    db.add(
                        RawJob(
                            source=connector.name,
                            source_job_id=source_job_id,
                            fetched_at=now,
                            payload=record.payload,
                            payload_hash=digest,
                        )
                    )
        status = "SUCCESS"
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        status = "FAILED"
        log.exception("Source fetch failed: %s", connector.name)

    finished = datetime.now(timezone.utc)
    elapsed_ms = int((time.monotonic() - started_clock) * 1000)
    source_run = RawSourceRun(
        pipeline_run_id=pipeline_run_id,
        source=connector.name,
        started_at=started,
        finished_at=finished,
        status=status,
        records_received=metrics["records_received"],
        records_inserted=metrics["records_inserted"],
        records_updated=metrics["records_updated"],
        records_rejected=metrics["records_rejected"],
        duplicates=metrics["duplicates"],
        error_message=error,
        execution_time_ms=elapsed_ms,
    )
    db.add(source_run)
    _upsert_source_status(db, connector.name, status, finished, metrics, error)
    db.commit()
    return {
        "source": connector.name,
        "status": status,
        **metrics,
        "execution_time_ms": elapsed_ms,
        "error": error,
    }


def run_pipeline(db: Session) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    started_clock = time.monotonic()
    run = PipelineRun(
        pipeline_name="jobpulse_ingestion", started_at=started, status="RUNNING"
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    total = {key: 0 for key in METRIC_KEYS}
    source_results = []
    connectors = enabled_connectors()

    if not connectors:
        run.status = "FAILED"
        run.error_message = "No ingestion sources are enabled"
        run.finished_at = datetime.now(timezone.utc)
        run.execution_time_ms = int((time.monotonic() - started_clock) * 1000)
        db.commit()
        return {"status": run.status, **total, "sources_succeeded": 0, "sources_failed": 0}

    for connector in connectors:
        result = process_source(db, connector, run.id)
        source_results.append(result)
        for key in METRIC_KEYS:
            total[key] += result[key]

    source_successes = sum(result["status"] == "SUCCESS" for result in source_results)
    source_failures = len(source_results) - source_successes
    run.status = (
        "FAILED"
        if source_failures == len(source_results)
        else "PARTIAL_SUCCESS"
        if source_failures
        else "SUCCESS"
    )
    for key, value in total.items():
        setattr(run, key, value)
    run.sources_succeeded = source_successes
    run.sources_failed = source_failures
    run.error_message = "; ".join(
        f"{result['source']}: {result['error']}"
        for result in source_results
        if result["error"]
    ) or None
    run.finished_at = datetime.now(timezone.utc)
    run.execution_time_ms = int((time.monotonic() - started_clock) * 1000)
    db.commit()
    return {
        "status": run.status,
        **total,
        "sources_succeeded": source_successes,
        "sources_failed": source_failures,
        "execution_time_ms": run.execution_time_ms,
        "sources": source_results,
    }
