from pathlib import Path

from alembic import command
from alembic.config import Config

from app.config import get_settings


def run_migrations() -> None:
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    config.attributes["database_url"] = get_settings().database_url
    command.upgrade(config, "head")


if __name__ == "__main__":
    run_migrations()
