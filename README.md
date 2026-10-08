# JobPulse — Automated hourly job-market intelligence

JobPulse is a Python data pipeline and API that ingests public job listings, validates and normalizes them, preserves source payloads and job history in PostgreSQL, builds dbt analytics, and serves the results through FastAPI. It is scheduled hourly, not real-time.

## Architecture and data flow

```text
Jobicy public API ─┐
                   ├─> GitHub Actions (hourly + manual) ─> Python ingestion
Arbeitnow API ─────┘                                  │
                                                      ├─> raw JSONB + source run history
                                                      ├─> validation / quality results
                                                      └─> normalized PostgreSQL staging
                                                              │
                                                              v
                                                        dbt analytics
                                                              │
                                                              v
                                                        FastAPI endpoints
```

## PostgreSQL schemas

- `raw.raw_jobs`: source JSONB, unique by source/job/content hash so unchanged payloads are not duplicated.
- `raw.raw_source_runs`: per-source status, timings, input/insert/update/reject/duplicate metrics.
- `staging.stg_jobs`: canonical jobs, unique on `(source, source_job_id)`, with first/last-seen, updated timestamps, and lifecycle status.
- `staging.stg_companies`, `staging.stg_locations`, `staging.stg_skills`, `staging.stg_job_skills`: normalized entities and the many-to-many skill mapping.
- `staging.stg_job_history`: job creation, update, close, and reactivation events with JSON snapshots.
- `monitoring.pipeline_runs`: pipeline-level metrics and honest success/partial/failure status.
- `monitoring.data_quality_results`: rejected input payloads and reasons.
- `monitoring.source_status`: latest source result and consecutive failure count.
- dbt builds `analytics.dim_company`, `dim_location`, `dim_skill`, `dim_date`, `fact_job`, `fact_job_skill`, and demand/hiring/salary marts.

Alembic owns schema creation and version tracking. Do not edit an applied migration; add a new revision when changing the schema.

## Sources

The connectors use the providers' public JSON endpoints without credentials:

- Jobicy: `https://jobicy.com/api/v2/remote-jobs`
- Arbeitnow: `https://www.arbeitnow.com/api/job-board-api`

Each response is checked for the expected collection shape, and each record is normalized independently so one malformed listing does not invalidate its source batch. The connector has a bounded timeout and retries transient HTTP failures with exponential backoff. A source failure is persisted while the other connector continues. Review and follow the providers' current use, attribution, and rate-limit terms before using the data outside this project. Returned API job records preserve their source and original listing URL.

Missing source IDs receive a deterministic ID: the normalized source URL where available, otherwise normalized title/company/location fields. The identity can change if a source changes all fields used by that fallback; a stable provider ID is preferred.

## Local development

Requirements: Docker Desktop with Compose v2. The checked-in example uses local-only placeholder credentials; replace `CHANGE_ME_LOCAL` before using pgAdmin beyond a private development machine.

```powershell
Copy-Item .env.example .env
# Set local POSTGRES_PASSWORD, PGADMIN_PASSWORD, and DATABASE_URL in .env.
docker compose up --build -d
```

Services:

- FastAPI and OpenAPI docs: `http://localhost:8000/docs`
- PostgreSQL: `localhost:5432`
- pgAdmin: `http://localhost:5050`

The one-shot `migrate` service applies Alembic migrations before the API and worker start. The worker fetches both public sources, stores the records, then runs `dbt build`. It repeats at `INGESTION_INTERVAL_MINUTES` (default 60). To run one immediate ingestion manually:

```powershell
docker compose exec api python -m scripts.run_ingestion
```

To inspect service state and logs:

```powershell
docker compose ps
docker compose logs --tail 100 api worker migrate postgres pgadmin
```

Stop the services with `docker compose down`. The named PostgreSQL volume is retained unless explicitly removed.

## Environment configuration

`.env.example` contains placeholders and local-development defaults only. The production connection string is provided to ingestion as the `DATABASE_URL` GitHub Actions secret; it is not committed or returned by the API. The dbt runner parses the connection URL in-process and passes its connection components to dbt without printing the password.

The API uses `CORS_ORIGINS` as a comma-separated allowlist. Set the production frontend origin explicitly if one is later added; this repository currently contains no frontend application.

## API

- `GET /health`
- `GET /jobs?page=1&page_size=50&title=&company=&location=&skill=&source=&status=&remote_type=`
- `GET /jobs/{job_id}`
- `GET /companies`, `GET /skills`, `GET /locations` (paginated)
- `GET /analytics/skills`
- `GET /analytics/skills/growth`
- `GET /analytics/companies`
- `GET /analytics/locations`
- `GET /analytics/salary` (actual reported salary values only, grouped by currency/period)
- `GET /pipeline/status`
- `GET /sources/status`

Analytics endpoints read dbt-built PostgreSQL models; they do not return demo data. Run at least one successful ingestion followed by `dbt build` before analytics results are available.

## CI, scheduling, and tests

- `.github/workflows/ci.yml` provisions PostgreSQL, applies migrations, runs the Python tests, and validates the dbt project.
- `.github/workflows/ingestion.yml` runs hourly and supports `workflow_dispatch`; it uses the `DATABASE_URL` repository secret and exits non-zero for failed/partial ingestion or dbt build.
- `py -3.12 -m pytest -q` runs unit tests. Database-backed end-to-end tests run when `TEST_DATABASE_URL` points to a disposable database named `jobpulse_test`; tests reset its JobPulse schemas.

The GitHub schedule is best-effort and may be delayed. No paid cloud services or always-on production ingestion worker are required by this design. Deployments are intentionally not performed as part of local development.
