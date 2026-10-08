# Local build and readiness checklist

## Local development
- [ ] Install Docker Desktop with Compose v2.
- [ ] Copy `.env.example` to `.env` and set local-only values.
- [ ] Run `docker compose up --build -d`.
- [ ] Check `http://localhost:8000/health` and `/docs`.
- [ ] Check PostgreSQL is healthy and pgAdmin is available at `http://localhost:5050`.
- [ ] Confirm the worker records source runs, pipeline metrics, and source health.
- [ ] Confirm dbt built the analytics facts, dimensions, marts, and tests.
- [ ] Run `py -3.12 -m pytest -q`.

## Before production deployment
- [ ] Review current public source terms, attribution requirements, and fair-use limits.
- [ ] Provision PostgreSQL and apply Alembic migrations.
- [ ] Configure the GitHub Actions `DATABASE_URL` secret.
- [ ] Run the ingestion workflow manually and inspect pipeline/source status.
- [ ] Deploy FastAPI and configure a strict CORS allowlist.
- [ ] Build/deploy a frontend separately if one is added to this repository.
- [ ] Verify production health, API data, analytics, and scheduled ingestion.

Deployment is intentionally not part of the local build verification.
