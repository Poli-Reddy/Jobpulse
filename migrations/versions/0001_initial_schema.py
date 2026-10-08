"""Create the initial JobPulse raw, staging, monitoring, and analytics schemas.

This is the immutable baseline for new installations. Changes after this revision
must be delivered in new Alembic revisions rather than editing this file.
"""

from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    from app import models  # noqa: F401
    from app.db import Base

    bind = op.get_bind()
    for schema in ("raw", "staging", "analytics", "monitoring"):
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    from app import models  # noqa: F401
    from app.db import Base

    Base.metadata.drop_all(bind=op.get_bind())
