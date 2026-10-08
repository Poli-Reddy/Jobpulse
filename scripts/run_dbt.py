import os
import shutil
import subprocess
from pathlib import Path

from sqlalchemy.engine import make_url

from app.config import get_settings


def run_dbt() -> None:
    url = make_url(get_settings().database_url)
    if not url.drivername.startswith("postgresql"):
        raise RuntimeError("dbt analytics models require PostgreSQL")
    dbt_environment = os.environ.copy()
    dbt_environment.update(
        {
            "DBT_HOST": url.host or "localhost",
            "DBT_PORT": str(url.port or 5432),
            "DBT_USER": url.username or "",
            "DBT_PASSWORD": url.password or "",
            "DBT_DATABASE": url.database or "",
            "DBT_SSLMODE": str(url.query.get("sslmode", "prefer")),
        }
    )
    root = Path(__file__).resolve().parents[1]
    dbt_executable = shutil.which("dbt")
    if dbt_executable is None:
        raise RuntimeError("dbt executable is not installed; install project requirements")
    subprocess.run(
        [
            dbt_executable,
            "build",
            "--project-dir",
            str(root / "dbt"),
            "--profiles-dir",
            str(root / "dbt"),
        ],
        cwd=root,
        env=dbt_environment,
        check=True,
    )


if __name__ == "__main__":
    run_dbt()
