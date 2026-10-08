select company_key, company_name, domain
from {{ ref('stg_companies') }}
