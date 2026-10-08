# Data model

`staging.stg_jobs` is the canonical job entity and is unique by `(source, source_job_id)`. The staging company, location, and skill tables hold normalized lookup records. `staging.stg_job_skills` is the many-to-many bridge. `staging.stg_job_history` captures lifecycle events and JSON snapshots.

`raw.raw_jobs` stores source payloads as JSONB, deduplicated by source identity and payload hash. `raw.raw_source_runs` records per-source metrics. The `monitoring` schema stores pipeline runs, source status, and data-quality rejection reasons.

dbt builds the analytical star:

```text
                 dim_company
                      |
 dim_location --- fact_job --- dim_date
                      |
                 fact_job_skill
                      |
                  dim_skill
```

The model deliberately keeps source identifiers because source systems can reuse titles and company names. Salary values remain source-reported and are grouped by currency and pay period rather than mixed.
