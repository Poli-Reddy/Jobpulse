import os
import socket
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

# Keep pytest away from the developer's .env database, which may be a real service.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://jobpulse:jobpulse-test@localhost:5432/jobpulse_test",
)


@pytest.fixture
def postgres_session() -> Iterator[Session]:
    test_url = os.environ.get("TEST_DATABASE_URL")
    if not test_url:
        pytest.skip("Set TEST_DATABASE_URL to the disposable jobpulse_test database")
    if make_url(test_url).database != "jobpulse_test":
        pytest.fail("Integration tests may only reset a database named jobpulse_test")
    url = make_url(test_url)
    try:
        with socket.create_connection((url.host or "localhost", url.port or 5432), timeout=1):
            pass
    except OSError as exc:
        pytest.skip(f"Disposable PostgreSQL test database is unavailable: {exc}")

    from app.db import Base
    from app import models  # noqa: F401

    engine = create_engine(test_url, pool_pre_ping=True)
    with engine.begin() as connection:
        for schema in ("analytics", "monitoring", "staging", "raw"):
            connection.execute(text(f"DROP SCHEMA IF EXISTS {schema} CASCADE"))
        for schema in ("raw", "staging", "analytics", "monitoring"):
            connection.execute(text(f"CREATE SCHEMA {schema}"))
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
