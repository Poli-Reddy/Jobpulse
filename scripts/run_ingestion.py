import json
import logging
import sys

from app.config import get_settings
from app.db import SessionLocal
from app.etl import run_pipeline
from app.logging_config import configure_logging
from scripts.run_dbt import run_dbt
from scripts.run_migrations import run_migrations


def main() -> int:
    configure_logging(get_settings().log_level)
    run_migrations()
    with SessionLocal() as db:
        result = run_pipeline(db)
    print(json.dumps(result, default=str))
    if result.get("sources_succeeded", 0):
        run_dbt()
    if result["status"] != "SUCCESS":
        logging.getLogger(__name__).error("Ingestion completed with status %s", result["status"])
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
