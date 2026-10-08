select id as company_key, name as company_name, domain
from {{ source('jobpulse_staging', 'stg_companies') }}
