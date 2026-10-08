# Architecture

## Layers

### Source
Public job APIs are external systems and are treated as unreliable dependencies.

### Raw
Every payload is preserved as JSON. This supports replay/debugging and protects against normalization bugs.

### Staging
PostgreSQL normalized `staging.stg_*` tables maintain companies, locations, jobs, skills, job-skill bridges, and job history.

### Monitoring
`monitoring.pipeline_runs`, `monitoring.source_status`, and `monitoring.data_quality_results` store run metrics, per-source health, and rejected records with reasons.

### Analytics
dbt builds BI-friendly views/tables in `analytics`.

### Serving
FastAPI exposes operational and analytical endpoints; Metabase serves business dashboards.

## Reliability principles
- bounded retries with exponential backoff
- per-source health tracking
- idempotent `(source, source_job_id)` identity
- payload hashes for raw deduplication
- historical lifecycle events for change detection
- validation before core writes
- no destructive delete when a source is temporarily unavailable
