select location_key, raw_location, normalized_location, city, country, remote
from {{ ref('stg_locations') }}
