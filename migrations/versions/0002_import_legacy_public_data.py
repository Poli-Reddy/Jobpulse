"""Move existing public-schema JobPulse data into the layered schemas."""

from alembic import op

revision = "0002_import_legacy_public_data"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $migration$
        BEGIN
          IF to_regclass('public.companies') IS NOT NULL THEN
            EXECUTE $sql$
              INSERT INTO staging.stg_companies
                (name, normalized_name, domain, created_at, updated_at)
              SELECT c.name, c.normalized_name, c.domain, now(), now()
              FROM public.companies c
              ON CONFLICT (normalized_name) DO NOTHING
            $sql$;
          END IF;

          IF to_regclass('public.locations') IS NOT NULL THEN
            EXECUTE $sql$
              INSERT INTO staging.stg_locations
                (raw_location, normalized_location, city, country, remote, normalized_key, created_at)
              SELECT l.raw_location,
                     regexp_replace(l.raw_location, 'Bangalore', 'Bengaluru', 'gi'),
                     l.city, l.country, l.remote,
                     btrim(lower(regexp_replace(
                       regexp_replace(l.raw_location, 'Bangalore', 'Bengaluru', 'gi'),
                       '[^a-zA-Z0-9]+', ' ', 'g'
                     ))) || '|remote=' || lower(l.remote::text),
                     now()
              FROM public.locations l
              ON CONFLICT (normalized_key) DO NOTHING
            $sql$;
          END IF;

          IF to_regclass('public.skills') IS NOT NULL THEN
            EXECUTE $sql$
              INSERT INTO staging.stg_skills (name, category)
              SELECT s.name, s.category
              FROM public.skills s
              ON CONFLICT (name) DO NOTHING
            $sql$;
          END IF;

          IF to_regclass('public.jobs') IS NOT NULL
             AND to_regclass('public.companies') IS NOT NULL
             AND to_regclass('public.locations') IS NOT NULL THEN
            EXECUTE $sql$
              INSERT INTO staging.stg_jobs
                (id, source, source_job_id, company_id, location_id, title, description,
                 job_url, employment_type, level, salary_min, salary_max, salary_currency,
                 salary_period, published_at, first_seen_at, last_seen_at, updated_at,
                 status, content_hash)
              SELECT j.id, j.source, j.source_job_id, sc.id, sl.id, j.title, j.description,
                     j.job_url, j.employment_type, j.level, j.salary_min, j.salary_max,
                     j.salary_currency, j.salary_period, j.published_at, j.first_seen_at,
                     j.last_seen_at, coalesce(j.last_seen_at, j.first_seen_at),
                     CASE upper(j.status)
                       WHEN 'CLOSED' THEN 'CLOSED'
                       WHEN 'NEW' THEN 'NEW'
                       WHEN 'UPDATED' THEN 'UPDATED'
                       WHEN 'REACTIVATED' THEN 'REACTIVATED'
                       ELSE 'ACTIVE'
                     END,
                     j.content_hash
              FROM public.jobs j
              JOIN public.companies c ON c.id = j.company_id
              JOIN staging.stg_companies sc ON sc.normalized_name = c.normalized_name
              JOIN public.locations l ON l.id = j.location_id
              JOIN staging.stg_locations sl
                ON sl.normalized_key =
                   btrim(lower(regexp_replace(
                     regexp_replace(l.raw_location, 'Bangalore', 'Bengaluru', 'gi'),
                     '[^a-zA-Z0-9]+', ' ', 'g'
                   ))) || '|remote=' || lower(l.remote::text)
              WHERE lower(j.source) <> 'remotive'
              ON CONFLICT (source, source_job_id) DO NOTHING
            $sql$;
            PERFORM setval(
              pg_get_serial_sequence('staging.stg_jobs', 'id'),
              greatest(coalesce((SELECT max(id) FROM staging.stg_jobs), 1), 1),
              EXISTS (SELECT 1 FROM staging.stg_jobs)
            );
          END IF;

          IF to_regclass('public.job_skills') IS NOT NULL
             AND to_regclass('public.jobs') IS NOT NULL
             AND to_regclass('public.skills') IS NOT NULL THEN
            EXECUTE $sql$
              INSERT INTO staging.stg_job_skills (job_id, skill_id)
              SELECT j.id, s.id
              FROM public.job_skills js
              JOIN public.jobs old_job ON old_job.id = js.job_id
              JOIN staging.stg_jobs j
                ON j.source = old_job.source AND j.source_job_id = old_job.source_job_id
              JOIN public.skills old_skill ON old_skill.id = js.skill_id
              JOIN staging.stg_skills s ON s.name = old_skill.name
              ON CONFLICT (job_id, skill_id) DO NOTHING
            $sql$;
          END IF;

          IF to_regclass('public.raw_jobs') IS NOT NULL THEN
            EXECUTE $sql$
              INSERT INTO raw.raw_jobs
                (source, source_job_id, fetched_at, payload, payload_hash)
              SELECT r.source, r.source_job_id, r.fetched_at, r.payload, r.payload_hash
              FROM public.raw_jobs r
              WHERE lower(r.source) <> 'remotive'
              ON CONFLICT (source, source_job_id, payload_hash) DO NOTHING
            $sql$;
          END IF;

          IF to_regclass('public.job_snapshots') IS NOT NULL
             AND to_regclass('public.jobs') IS NOT NULL THEN
            EXECUTE $sql$
              INSERT INTO staging.stg_job_history
                (job_id, event_type, occurred_at, content_hash, snapshot)
              SELECT j.id, 'UPDATED', h.captured_at, h.content_hash,
                     jsonb_build_object(
                       'title', h.title, 'description', h.description,
                       'salary_min', h.salary_min, 'salary_max', h.salary_max,
                       'status', h.status
                     )
              FROM public.job_snapshots h
              JOIN public.jobs old_job ON old_job.id = h.job_id
              JOIN staging.stg_jobs j
                ON j.source = old_job.source AND j.source_job_id = old_job.source_job_id
            $sql$;
          END IF;

          IF to_regclass('public.pipeline_runs') IS NOT NULL THEN
            EXECUTE $sql$
              INSERT INTO monitoring.pipeline_runs
                (pipeline_name, started_at, finished_at, status, records_received,
                 records_inserted, records_updated, records_rejected, duplicates,
                 sources_succeeded, sources_failed, error_message)
              SELECT pipeline_name, started_at, finished_at,
                     CASE WHEN upper(status) = 'RUNNING' THEN 'FAILED'
                          WHEN upper(status) IN ('SUCCESS', 'FAILED', 'PARTIAL_SUCCESS') THEN upper(status)
                          ELSE 'FAILED' END,
                     coalesce(records_received, 0), coalesce(records_loaded, 0), 0,
                     coalesce(records_rejected, 0), 0, 0, 0, error_message
              FROM public.pipeline_runs
            $sql$;
          END IF;

          IF to_regclass('public.source_health') IS NOT NULL THEN
            EXECUTE $sql$
              INSERT INTO monitoring.source_status
                (source, last_run_at, last_success_at, last_failure_at, status,
                 records_received, records_inserted, records_updated, records_rejected,
                 duplicates, consecutive_failures, last_error)
              SELECT source,
                     greatest(last_success_at, last_failure_at),
                     last_success_at, last_failure_at,
                     CASE WHEN last_failure_at > coalesce(last_success_at, '-infinity'::timestamptz)
                          THEN 'FAILED' ELSE 'SUCCESS' END,
                     0, 0, 0, 0, 0,
                     coalesce(consecutive_failures, 0), last_error
              FROM public.source_health
              WHERE lower(source) <> 'remotive'
              ON CONFLICT (source) DO NOTHING
            $sql$;
          END IF;
        END
        $migration$;
        """
    )


def downgrade() -> None:
    # The copy is intentionally irreversible; imported records are valid history.
    pass
