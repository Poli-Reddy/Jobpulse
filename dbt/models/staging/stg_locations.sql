select
    id as location_key,
    raw_location,
    normalized_location,
    city,
    country,
    remote
from {{ source('jobpulse_staging', 'stg_locations') }}
