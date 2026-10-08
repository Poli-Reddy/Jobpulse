select
    date_trunc('month', j.published_at)::date as month,
    s.skill_name as skill,
    count(distinct fs.job_key) as job_count
from {{ ref('fact_job_skill') }} fs
join {{ ref('fact_job') }} j on j.job_key = fs.job_key
join {{ ref('dim_skill') }} s on s.skill_key = fs.skill_key
where j.published_at is not null
group by 1, 2
