# Deployment readiness notes

Deployment is deliberately deferred. The project has been verified locally with Docker Compose, PostgreSQL, live public-source ingestion, dbt, and FastAPI.

## Intended deployment sequence

1. Provision a PostgreSQL database on the selected provider and protect the connection details.
2. Configure `DATABASE_URL` as a GitHub Actions repository secret.
3. Run the ingestion workflow manually and verify pipeline/source status.
4. Deploy FastAPI on the chosen backend host and check `/health` and `/docs`.
5. Configure the production CORS allowlist.
6. Deploy a frontend only after one is added to this repository.
7. Enable the best-effort hourly schedule and monitor data freshness.

Render's Python runtime is pinned by the repository-root `.python-version` file
to Python 3.12.8. If a Render service-level `PYTHON_VERSION` environment
variable is set, keep it aligned with this file; Render uses that variable in
preference to the repository pin.

No production service, database, or repository secret has been configured by this local project.

## Operational constraints

- GitHub scheduled workflows may be delayed; ingestion is hourly polling, not real-time.
- The worker and API should use the same migrated PostgreSQL database.
- Apply Alembic migrations before starting API/worker processes.
- Do not commit `.env` or place secrets in workflow YAML.
- Review source terms, attribution requirements, and rate limits before external use.
- Keep the production CORS allowlist narrow; do not use `*` for credentials-enabled access.
