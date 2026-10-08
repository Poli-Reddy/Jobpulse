import logging
import os
import time

from app.config import get_settings
from app.db import SessionLocal
from app.etl import run_pipeline
from scripts.run_dbt import run_dbt
from scripts.run_migrations import run_migrations

logging.basicConfig(
    level=getattr(logging, get_settings().log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    run_migrations()
    interval_minutes = int(
        os.getenv("INGESTION_INTERVAL_MINUTES")
        or os.getenv("SCHEDULER_INTERVAL_MINUTES")
        or "60"
    )
    while True:
        try:
            with SessionLocal() as db:
                result = run_pipeline(db)
            logger.info("Worker run complete: %s", result)
            if result.get("sources_succeeded", 0):
                run_dbt()
        except Exception:
            logger.exception("Worker run or dbt build failed")
        time.sleep(interval_minutes * 60)


if __name__ == "__main__":
    main()
