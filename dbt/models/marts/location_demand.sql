select
    location,
    count(*) as job_count,
    count(*) filter (where status <> 'CLOSED') as active_jobs,
    count(*) filter (where remote) as remote_jobs
from {{ ref('fact_job') }}
group by location
