from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.connectors import SourceRecord
from app.etl import run_pipeline
from app.main import app
from app.models import (
    DataQualityResult,
    PipelineRun,
    RawJob,
    RawSourceRun,
    SourceStatus,
    StgJob,
    StgJobHistory,
    StgJobSkill,
    StgSkill,
)
from app.schemas import NormalizedJob


class FixedConnector:
    name = "arbeitnow"

    def __init__(self, records):
        self.records = records

    def fetch(self):
        return self.records


class FailedConnector:
    name = "jobicy"

    def fetch(self):
        raise TimeoutError("test source timeout")


def make_record(description="Python PostgreSQL"):
    payload = {
        "slug": "stable-job-1",
        "title": "Data Engineer",
        "company_name": "Acme Inc.",
        "location": "Bangalore, India",
        "description": description,
        "url": "https://example.org/jobs/stable-job-1",
        "created_at": "2026-10-01T00:00:00Z",
        "salary_min": 75000,
        "salary_max": 95000,
        "currency": "USD",
        "salary_period": "yearly",
    }
    job = NormalizedJob(
        source="arbeitnow",
        source_job_id="stable-job-1",
        title="Data Engineer",
        company_name="Acme Inc.",
        location="Bangalore, India",
        description=description,
        job_url=payload["url"],
        published_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
        salary_min=75000,
        salary_max=95000,
        salary_currency="USD",
        salary_period="yearly",
        skills=["Python", "PostgreSQL"]
        if "PostgreSQL" in description
        else ["Python", "SQL"],
    )
    return SourceRecord(payload=payload, job=job)


def test_idempotency_history_dbt_analytics_and_api(
    postgres_session, monkeypatch
):
    connector = FixedConnector([make_record()])
    monkeypatch.setattr("app.etl.enabled_connectors", lambda: [connector])

    first = run_pipeline(postgres_session)
    second = run_pipeline(postgres_session)
    assert first["records_inserted"] == 1
    assert second["records_inserted"] == 0
    assert second["records_updated"] == 0
    assert second["duplicates"] == 1
    assert postgres_session.query(StgJob).count() == 1
    assert postgres_session.query(RawJob).count() == 1
    assert postgres_session.query(StgJobSkill).count() == 2
    assert postgres_session.query(RawSourceRun).count() == 2
    job = postgres_session.query(StgJob).one()
    assert job.status == "ACTIVE"
    assert postgres_session.query(StgJobHistory).count() == 2
    assert job.first_seen_at <= job.last_seen_at
    assert job.updated_at <= job.last_seen_at

    connector.records = [make_record("Python SQL")]
    updated = run_pipeline(postgres_session)
    assert updated["records_updated"] == 1
    postgres_session.refresh(job)
    assert job.status == "UPDATED"
    assert job.updated_at == job.last_seen_at
    assert postgres_session.query(StgJobHistory).count() == 3
    skill_names = {
        name
        for (name,) in postgres_session.query(StgSkill.name)
        .join(StgJobSkill, StgJobSkill.skill_id == StgSkill.id)
        .filter(StgJobSkill.job_id == job.id)
        .all()
    }
    assert skill_names == {"Python", "SQL"}

    from scripts.run_dbt import run_dbt

    run_dbt()
    with TestClient(app) as client:
        assert client.get("/health").json() == {
            "status": "ok",
            "database": "connected",
        }
        listing = client.get("/jobs?page=1&page_size=1").json()
        assert listing["total"] == 1
        assert listing["items"][0]["title"] == "Data Engineer"
        detail = client.get(f"/jobs/{listing['items'][0]['id']}")
        assert detail.status_code == 200
        assert detail.json()["source_job_id"] == "stable-job-1"
        assert client.get("/jobs?skill=Python").json()["total"] == 1
        assert client.get("/jobs?source=unknown").json()["total"] == 0
        assert client.get("/jobs?page_size=101").status_code == 422
        assert client.get("/jobs?page=0").status_code == 422
        assert client.get("/jobs?remote_type=unknown").status_code == 422
        assert client.get("/jobs/99999").status_code == 404
        assert client.get("/companies").json()["total"] == 1
        assert client.get("/skills").json()["total"] == 2
        assert client.get("/locations").json()["total"] == 1
        assert client.get("/analytics/skills").json()
        assert client.get("/analytics/skills/growth").json()
        assert client.get("/analytics/companies").json()
        assert client.get("/analytics/locations").json()
        salary = client.get("/analytics/salary").json()
        assert salary[0]["jobs_with_salary"] == 1
        assert float(salary[0]["avg_salary_min"]) == 75000
        assert client.get("/pipeline/status").json()["records_updated"] == 1
        assert client.get("/sources/status").json()[0]["source"] == "arbeitnow"


def test_one_source_failure_does_not_block_other_source(postgres_session, monkeypatch):
    valid = FixedConnector([make_record()])
    monkeypatch.setattr(
        "app.etl.enabled_connectors", lambda: [FailedConnector(), valid]
    )

    result = run_pipeline(postgres_session)

    assert result["status"] == "PARTIAL_SUCCESS"
    assert result["sources_succeeded"] == 1
    assert result["sources_failed"] == 1
    assert result["records_inserted"] == 1
    assert postgres_session.query(StgJob).count() == 1
    assert postgres_session.query(PipelineRun).one().status == "PARTIAL_SUCCESS"
    assert postgres_session.query(SourceStatus).filter_by(source="jobicy").one().status == "FAILED"


def test_malformed_records_are_reported_and_raw_payload_is_kept(postgres_session, monkeypatch):
    bad = SourceRecord(
        payload={"title": "missing critical fields"},
        job=None,
        error="title/company/url are required",
    )
    monkeypatch.setattr(
        "app.etl.enabled_connectors", lambda: [FixedConnector([bad])]
    )

    result = run_pipeline(postgres_session)

    assert result["records_received"] == 1
    assert result["records_rejected"] == 1
    assert postgres_session.query(RawJob).count() == 1
    quality = postgres_session.query(DataQualityResult).one()
    assert quality.reason == "title/company/url are required"


def test_explicit_closed_status_is_historical_and_missing_jobs_stay_open(
    postgres_session, monkeypatch
):
    active = make_record()
    monkeypatch.setattr(
        "app.etl.enabled_connectors", lambda: [FixedConnector([active])]
    )
    run_pipeline(postgres_session)
    job = postgres_session.query(StgJob).one()
    assert job.status == "NEW"

    closed = make_record()
    closed.payload["status"] = "closed"
    monkeypatch.setattr(
        "app.etl.enabled_connectors", lambda: [FixedConnector([closed])]
    )
    run_pipeline(postgres_session)
    postgres_session.refresh(job)
    assert job.status == "CLOSED"
    assert [row.event_type for row in postgres_session.query(StgJobHistory).order_by(
        StgJobHistory.id
    )] == ["NEW", "CLOSED"]

    active.payload.pop("status", None)
    monkeypatch.setattr(
        "app.etl.enabled_connectors", lambda: [FixedConnector([active])]
    )
    run_pipeline(postgres_session)
    postgres_session.refresh(job)
    assert job.status == "REACTIVATED"
    assert [row.event_type for row in postgres_session.query(StgJobHistory).order_by(
        StgJobHistory.id
    )] == ["NEW", "CLOSED", "REACTIVATED"]

    monkeypatch.setattr("app.etl.enabled_connectors", lambda: [FixedConnector([])])
    run_pipeline(postgres_session)
    postgres_session.refresh(job)
    assert job.status == "REACTIVATED"
