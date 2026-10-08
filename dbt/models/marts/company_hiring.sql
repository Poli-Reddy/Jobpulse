select
    company_name,
    count(*) as job_count,
    count(*) filter (where status <> 'CLOSED') as active_jobs,
    min(first_seen_at) as first_seen_at,
    max(last_seen_at) as last_seen_at
from {{ ref('fact_job') }}
group by company_name
