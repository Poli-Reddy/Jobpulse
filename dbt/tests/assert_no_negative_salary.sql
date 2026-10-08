select job_key, salary_min, salary_max
from {{ ref('fact_job') }}
where salary_min < 0 or salary_max < 0
