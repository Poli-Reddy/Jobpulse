select
    s.skill_name as skill,
    count(distinct fs.job_key) as job_count,
    count(distinct fs.job_key) filter (where j.status <> 'CLOSED') as active_job_count
from {{ ref('fact_job_skill') }} fs
join {{ ref('dim_skill') }} s on s.skill_key = fs.skill_key
join {{ ref('fact_job') }} j on j.job_key = fs.job_key
group by s.skill_name
