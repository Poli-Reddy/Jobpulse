# Optional Metabase dashboard queries

The Docker Compose development stack does not start a Metabase server. If you run Metabase separately, connect it to the local PostgreSQL service and use the analytics models created by dbt:

- `analytics.skill_demand`: tracked skill counts
- `analytics.skill_growth`: jobs by published month and skill
- `analytics.company_hiring`: jobs by company
- `analytics.location_demand`: jobs by location and remote count
- `analytics.daily_job_trend`: jobs first observed per day
- `analytics.salary_demand`: source-reported salary metrics grouped by currency and period

Example cards are in `dashboard_queries.sql`. They contain no fabricated records.
