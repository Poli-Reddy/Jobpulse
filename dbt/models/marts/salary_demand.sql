select
    salary_currency as currency,
    salary_period,
    count(*) filter (
        where salary_min is not null or salary_max is not null
    ) as jobs_with_salary,
    avg(salary_min) as avg_salary_min,
    avg(salary_max) as avg_salary_max
from {{ ref('fact_job') }}
where salary_min is not null or salary_max is not null
group by salary_currency, salary_period
