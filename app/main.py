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
    search: str | None = Query(None, min_length=1, max_length=200),
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
        "search": f"%{search}%" if search else None,
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
          AND (:search IS NULL OR lower(j.title) LIKE lower(:search)
                              OR lower(j.description) LIKE lower(:search)
                              OR lower(c.name) LIKE lower(:search))
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
                   j.salary_currency, j.first_seen_at, j.status
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
    row = db.execute(
        text(
            """
            SELECT j.id, j.source, j.source_job_id, j.title, j.description, j.status,
                   j.job_url, j.salary_min, j.salary_max, j.salary_currency,
                   j.salary_period, j.employment_type, j.level, j.published_at,
                   j.first_seen_at, j.last_seen_at, j.updated_at,
                   c.name AS company, c.domain AS company_domain,
                   l.raw_location AS location, l.normalized_location,
                   l.remote,
                   coalesce(array_agg(s.name ORDER BY s.name)
                       FILTER (WHERE s.name IS NOT NULL), ARRAY[]::varchar[]) AS skills
            FROM staging.stg_jobs j
            JOIN staging.stg_companies c ON c.id = j.company_id
            JOIN staging.stg_locations l ON l.id = j.location_id
            LEFT JOIN staging.stg_job_skills js ON js.job_id = j.id
            LEFT JOIN staging.stg_skills s ON s.id = js.skill_id
            WHERE j.id = :job_id
            GROUP BY j.id, c.id, l.id
            """
        ),
        {"job_id": job_id},
    ).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return dict(row)


@app.get("/companies")
def companies(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    total = db.query(StgCompany).count()
    rows = db.execute(
        text(
            """
            SELECT c.id, c.name, c.domain,
                   count(DISTINCT j.id) FILTER (WHERE j.status <> 'CLOSED') AS active_jobs,
                   count(DISTINCT j.id) FILTER (WHERE j.status = 'NEW') AS new_jobs,
                   count(DISTINCT j.location_id) AS location_count,
                   ARRAY(
                       SELECT s.name
                       FROM staging.stg_jobs sj
                       JOIN staging.stg_job_skills js ON js.job_id = sj.id
                       JOIN staging.stg_skills s ON s.id = js.skill_id
                       WHERE sj.company_id = c.id AND sj.status <> 'CLOSED'
                       GROUP BY s.name
                       ORDER BY count(*) DESC, s.name
                       LIMIT 3
                   ) AS top_skills
            FROM staging.stg_companies c
            LEFT JOIN staging.stg_jobs j ON j.company_id = c.id
            GROUP BY c.id
            ORDER BY c.name
            LIMIT :limit OFFSET :offset
            """
        ),
        {"limit": page_size, "offset": (page - 1) * page_size},
    ).mappings()
    return {
        "items": [dict(row) for row in rows],
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
            "SELECT s.id, s.name, s.category, count(DISTINCT js.job_id) AS job_count "
            "FROM staging.stg_skills s "
            "JOIN staging.stg_job_skills js ON js.skill_id=s.id "
            "GROUP BY s.id ORDER BY job_count DESC, s.name LIMIT :limit OFFSET :offset"
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
    rows = db.execute(
        text(
            """
            SELECT l.id, l.normalized_location AS name, l.raw_location, l.remote,
                   count(DISTINCT j.id) AS job_count,
                   ARRAY(
                       SELECT s.name
                       FROM staging.stg_jobs sj
                       JOIN staging.stg_job_skills js ON js.job_id = sj.id
                       JOIN staging.stg_skills s ON s.id = js.skill_id
                       WHERE sj.location_id = l.id
                       GROUP BY s.name
                       ORDER BY count(*) DESC, s.name
                       LIMIT 3
                   ) AS top_skills
            FROM staging.stg_locations l
            LEFT JOIN staging.stg_jobs j ON j.location_id = l.id
            GROUP BY l.id
            ORDER BY l.normalized_location
            LIMIT :limit OFFSET :offset
            """
        ),
        {"limit": page_size, "offset": (page - 1) * page_size},
    ).mappings()
    return {
        "items": [dict(row) for row in rows],
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


@app.get("/analytics/jobs/trend")
def analytics_job_trend(limit: int = Query(90, ge=1, le=366), db: Session = Depends(get_db)):
    rows = db.execute(
        text(
            "SELECT day, jobs_first_seen FROM analytics.daily_job_trend "
            "ORDER BY day DESC LIMIT :limit"
        ),
        {"limit": limit},
    )
    return [dict(row._mapping) for row in rows][::-1]


@app.get("/analytics/overview")
def analytics_overview(db: Session = Depends(get_db)):
    counts = db.execute(
        text(
            """
            SELECT count(*) FILTER (WHERE status <> 'CLOSED') AS active_jobs,
                   count(*) FILTER (WHERE status = 'NEW') AS new_jobs,
                   count(DISTINCT company_id) FILTER (WHERE status <> 'CLOSED')
                       AS companies_hiring
            FROM staging.stg_jobs
            """
        )
    ).mappings().one()
    skills_count = db.execute(text("SELECT count(*) FROM staging.stg_skills")).scalar_one()
    sources_count = db.execute(
        text("SELECT count(*) FROM monitoring.source_status WHERE status = 'SUCCESS'")
    ).scalar_one()
    latest_run = db.query(PipelineRun).order_by(PipelineRun.started_at.desc()).first()
    return {
        **dict(counts),
        "tracked_skills": skills_count,
        "sources_succeeded": sources_count,
        "last_pipeline_run": latest_run.started_at if latest_run else None,
    }


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
