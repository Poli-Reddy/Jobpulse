select skill_key, skill_name, category
from {{ ref('stg_skills') }}
