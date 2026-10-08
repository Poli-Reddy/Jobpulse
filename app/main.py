import logging
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import (
    PipelineRun,
    SourceStatus,
    StgCompany,
    StgJob,
    StgLocation,
)

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="JobPulse API", version="2.0.0", lifespan=lifespan)
settings = get_settings()
origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(request: Request, exc: SQLAlchemyError):
    log.error(
        "Database request failed: path=%s error_type=%s",
        request.url.path,
        type(exc).__name__,
    )
    return JSONResponse(
        status_code=503,
        content={
            "detail": {
                "code": "database_unavailable",
                "message": "The requested data is temporarily unavailable.",
            }
        },
    )


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except SQLAlchemyError as exc:
        log.error("Health check database query failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=503,
            detail={"status": "error", "database": "disconnected"},
        ) from exc


@app.get("/jobs")
def jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    limit: int | None = Query(None, ge=1, le=100),
    source: str | None = Query(None, min_length=1, max_length=50),
    title: str | None = Query(None, min_length=1, max_length=200),
    company: str | None = Query(None, min_length=1, max_length=200),
    location: str | None = Query(None, min_length=1, max_length=200),
    skill: str | None = Query(None, min_length=1, max_length=120),
    status: Literal["NEW", "ACTIVE", "UPDATED", "CLOSED", "REACTIVATED"] | None = None,
    remote_type: Literal["remote", "hybrid", "onsite"] | None = None,
    db: Session = Depends(get_db),
):
    size = limit or page_size
    params = {
        "source": source,
        "title": f"%{title}%" if title else None,
        "company": f"%{company}%" if company else None,
        "location": f"%{location}%" if location else None,
        "skill": skill,
        "status": status,
        "remote": True if remote_type == "remote" else False if remote_type == "onsite" else None,
        "hybrid": remote_type == "hybrid",
        "limit": size,
        "offset": (page - 1) * size,
    }
    filters = """
        WHERE (:source IS NULL OR j.source = :source)
          AND (:title IS NULL OR lower(j.title) LIKE lower(:title))
          AND (:company IS NULL OR lower(c.name) LIKE lower(:company))
          AND (:location IS NULL OR lower(l.normalized_location) LIKE lower(:location)
                                  OR lower(l.raw_location) LIKE lower(:location))
          AND (:skill IS NULL OR EXISTS (
                SELECT 1 FROM staging.stg_job_skills js
                JOIN staging.stg_skills s ON s.id = js.skill_id
                WHERE js.job_id = j.id AND lower(s.name) = lower(:skill)))
          AND (:status IS NULL OR j.status = :status)
          AND (:remote IS NULL OR l.remote = :remote)
          AND (NOT :hybrid OR lower(l.raw_location) LIKE '%hybrid%')
    """
    total = db.execute(
        text(
            "SELECT count(*) FROM staging.stg_jobs j "
            "JOIN staging.stg_companies c ON c.id=j.company_id "
            "JOIN staging.stg_locations l ON l.id=j.location_id " + filters
        ),
        params,
    ).scalar_one()
    rows = db.execute(
        text(
            """
            SELECT j.id, j.source, j.source_job_id, j.title, c.name AS company,
                   l.raw_location AS location, l.normalized_location, l.remote,
                   j.job_url, j.published_at, j.salary_min, j.salary_max,
                   j.salary_currency, j.status
            FROM staging.stg_jobs j
            JOIN staging.stg_companies c ON c.id=j.company_id
            JOIN staging.stg_locations l ON l.id=j.location_id
            """
            + filters
            + " ORDER BY j.published_at DESC NULLS LAST, j.id DESC LIMIT :limit OFFSET :offset"
        ),
        params,
    )
    return {
        "items": [dict(row._mapping) for row in rows],
        "total": total,
        "page": page,
        "page_size": size,
    }


@app.get("/jobs/{job_id}")
def job_detail(job_id: int, db: Session = Depends(get_db)):
    item = db.get(StgJob, job_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": item.id,
        "source": item.source,
        "source_job_id": item.source_job_id,
        "title": item.title,
        "description": item.description,
        "status": item.status,
        "job_url": item.job_url,
        "company_id": item.company_id,
        "location_id": item.location_id,
        "salary_min": item.salary_min,
        "salary_max": item.salary_max,
        "salary_currency": item.salary_currency,
        "published_at": item.published_at,
        "first_seen_at": item.first_seen_at,
        "last_seen_at": item.last_seen_at,
        "updated_at": item.updated_at,
    }


@app.get("/companies")
def companies(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    total = db.query(StgCompany).count()
    rows = (
        db.query(StgCompany.id, StgCompany.name, StgCompany.domain)
        .order_by(StgCompany.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [{"id": row.id, "name": row.name, "domain": row.domain} for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@app.get("/skills")
def skills(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    total = db.execute(
        text(
            "SELECT count(DISTINCT s.id) FROM staging.stg_skills s "
            "JOIN staging.stg_job_skills js ON js.skill_id=s.id"
        )
    ).scalar_one()
    rows = db.execute(
        text(
            "SELECT DISTINCT s.id, s.name, s.category FROM staging.stg_skills s "
            "JOIN staging.stg_job_skills js ON js.skill_id=s.id "
            "ORDER BY s.name LIMIT :limit OFFSET :offset"
        ),
        {"limit": page_size, "offset": (page - 1) * page_size},
    )
    return {
        "items": [dict(row._mapping) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@app.get("/locations")
def locations(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    total = db.query(StgLocation).count()
    rows = (
        db.query(StgLocation)
        .order_by(StgLocation.normalized_location)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [
            {
                "id": row.id,
                "name": row.normalized_location,
                "raw_location": row.raw_location,
                "remote": row.remote,
            }
            for row in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@app.get("/analytics/skills")
def analytics_skills(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    rows = db.execute(
        text(
            "SELECT skill, job_count FROM analytics.skill_demand "
            "ORDER BY job_count DESC, skill LIMIT :limit"
        ),
        {"limit": limit},
    )
    return [dict(row._mapping) for row in rows]


@app.get("/analytics/skills/growth")
def analytics_skills_growth(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        text(
            "SELECT month, skill, job_count FROM analytics.skill_growth "
            "ORDER BY month DESC, job_count DESC, skill LIMIT :limit"
        ),
        {"limit": limit},
    )
    return [dict(row._mapping) for row in rows]


@app.get("/analytics/companies")
def analytics_companies(
    limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)
):
    rows = db.execute(
        text(
            "SELECT company_name AS company, job_count, active_jobs "
            "FROM analytics.company_hiring "
            "ORDER BY job_count DESC, company_name LIMIT :limit"
        ),
        {"limit": limit},
    )
    return [dict(row._mapping) for row in rows]


@app.get("/analytics/locations")
def analytics_locations(
    limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)
):
    rows = db.execute(
        text(
            "SELECT location, job_count, remote_jobs FROM analytics.location_demand "
            "ORDER BY job_count DESC, location LIMIT :limit"
        ),
        {"limit": limit},
    )
    return [dict(row._mapping) for row in rows]


@app.get("/analytics/salary")
def analytics_salary(db: Session = Depends(get_db)):
    rows = db.execute(
        text(
            "SELECT currency, salary_period, jobs_with_salary, avg_salary_min, avg_salary_max "
            "FROM analytics.salary_demand ORDER BY currency, salary_period"
        )
    )
    return [dict(row._mapping) for row in rows]


@app.get("/pipeline/status")
def pipeline_status(db: Session = Depends(get_db)):
    run = db.query(PipelineRun).order_by(PipelineRun.started_at.desc()).first()
    if run is None:
        return {"status": "NO_RUN", "last_run": None}
    return {
        "status": run.status,
        "pipeline_name": run.pipeline_name,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "records_received": run.records_received,
        "records_inserted": run.records_inserted,
        "records_updated": run.records_updated,
        "records_rejected": run.records_rejected,
        "duplicates": run.duplicates,
        "sources_succeeded": run.sources_succeeded,
        "sources_failed": run.sources_failed,
        "execution_time_ms": run.execution_time_ms,
        "error_message": run.error_message,
    }


@app.get("/sources/status")
def sources_status(db: Session = Depends(get_db)):
    rows = db.query(SourceStatus).order_by(SourceStatus.source.asc()).all()
    return [
        {
            "source": row.source,
            "status": row.status,
            "last_run_at": row.last_run_at,
            "last_success_at": row.last_success_at,
            "last_failure_at": row.last_failure_at,
            "records_received": row.records_received,
            "records_inserted": row.records_inserted,
            "records_updated": row.records_updated,
            "records_rejected": row.records_rejected,
            "duplicates": row.duplicates,
            "consecutive_failures": row.consecutive_failures,
            "error": row.last_error,
        }
        for row in rows
    ]
