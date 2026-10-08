select id as skill_key, name as skill_name, category
from {{ source('jobpulse_staging', 'stg_skills') }}
