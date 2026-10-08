select
    js.job_key,
    js.skill_key
from {{ ref('stg_job_skills') }} js
join {{ ref('fact_job') }} j on j.job_key = js.job_key
join {{ ref('dim_skill') }} s on s.skill_key = js.skill_key
