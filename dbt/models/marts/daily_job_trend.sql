select
    first_seen_at::date as day,
    count(*) as jobs_first_seen
from {{ ref('fact_job') }}
group by first_seen_at::date
