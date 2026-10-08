select job_key, salary_min, salary_max
from {{ ref('fact_job') }}
where salary_min is not null
  and salary_max is not null
  and salary_max < salary_min
