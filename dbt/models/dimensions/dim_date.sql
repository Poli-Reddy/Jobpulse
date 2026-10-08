with job_dates as (
    select distinct published_at::date as date_day
    from {{ ref('stg_jobs') }}
    where published_at is not null
)
select
    to_char(date_day, 'YYYYMMDD')::integer as date_key,
    date_day,
    extract(year from date_day)::integer as year,
    extract(quarter from date_day)::integer as quarter,
    extract(month from date_day)::integer as month,
    extract(day from date_day)::integer as day,
    extract(isodow from date_day)::integer as day_of_week
from job_dates
