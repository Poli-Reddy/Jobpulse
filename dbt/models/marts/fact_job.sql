select
    j.job_key,
    j.source,
    j.source_job_id,
    j.title,
    j.company_id as company_key,
    c.company_name,
    j.location_id as location_key,
    l.normalized_location as location,
    l.remote,
    j.employment_type,
    j.level,
    j.salary_min,
    j.salary_max,
    j.salary_currency,
    j.salary_period,
    d.date_key as published_date_key,
    j.published_at,
    j.first_seen_at,
    j.last_seen_at,
    j.updated_at,
    j.status,
    j.job_url
from {{ ref('stg_jobs') }} j
join {{ ref('dim_company') }} c on c.company_key = j.company_id
join {{ ref('dim_location') }} l on l.location_key = j.location_id
left join {{ ref('dim_date') }} d on d.date_day = j.published_at::date
