"""Retain only the public sources supported by the current ingestion pipeline."""

from alembic import op

revision = "0003_prune_sources"
down_revision = "0002_import_legacy_public_data"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM staging.stg_jobs
        WHERE source NOT IN ('jobicy', 'arbeitnow');

        DELETE FROM raw.raw_jobs
        WHERE source NOT IN ('jobicy', 'arbeitnow');

        DELETE FROM monitoring.source_status
        WHERE source NOT IN ('jobicy', 'arbeitnow');

        DELETE FROM staging.stg_companies c
        WHERE NOT EXISTS (
          SELECT 1 FROM staging.stg_jobs j WHERE j.company_id = c.id
        );

        DELETE FROM staging.stg_locations l
        WHERE NOT EXISTS (
          SELECT 1 FROM staging.stg_jobs j WHERE j.location_id = l.id
        );

        DELETE FROM staging.stg_skills s
        WHERE NOT EXISTS (
          SELECT 1 FROM staging.stg_job_skills js WHERE js.skill_id = s.id
        );
        """
    )


def downgrade() -> None:
    # Unsupported historical source records are intentionally not restored.
    pass
