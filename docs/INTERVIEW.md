# Interview notes

## Why PostgreSQL?
The job, company, location, and skill data is relational and benefits from transactions, constraints, JSONB payload storage, and SQL analytics.

## Why raw, staging, monitoring, and analytics schemas?
Raw payloads preserve source records for audit/reprocessing. Staging is the validated canonical layer. Monitoring records source and pipeline health plus data-quality failures. dbt creates explicit analytical dimensions, facts, and marts.

## How is ingestion idempotent?
Canonical jobs are unique by `(source, source_job_id)`. Raw payload observations are unique by source identity plus canonical payload hash. Sources without IDs get a deterministic fallback based on their URL or normalized title/company/location.

## How is job history tracked?
First/last-seen and updated timestamps live on the canonical job. Creation, changed content, explicit closure, and reactivation are captured as history events with snapshots.

## What happens when a source fails?
Retries are bounded. Each connector runs independently; a failed source is recorded as failed, while the other connector continues. Missing listings do not close jobs.

## Why deterministic skill extraction?
A controlled alias dictionary and token-boundary matching provide explainable extraction without LLMs. Skills are normalized and stored through a job-skill bridge table for analytics.

## Why dbt?
Version-controlled SQL models build tested dimensions, facts, and analytic marts from normalized staging data.

## Why GitHub Actions?
It runs best-effort hourly ingestion and supports manual triggers without a permanently running scheduler. This is hourly polling, not real-time streaming.

## How would it scale?
Measure first. If source volume or query workloads require it, consider partitioning historical raw records, incremental analytical builds, and separating serving/analytics workloads while retaining source isolation and data contracts.
