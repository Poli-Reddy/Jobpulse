select job_id as job_key, skill_id as skill_key
from {{ source('jobpulse_staging', 'stg_job_skills') }}
