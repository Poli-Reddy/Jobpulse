from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.db import get_db
from app.main import app


def test_required_routes_are_exposed():
    paths = {route.path for route in app.routes}
    required = {
        "/health",
        "/jobs",
        "/jobs/{job_id}",
        "/companies",
        "/skills",
        "/locations",
        "/analytics/skills",
        "/analytics/skills/growth",
        "/analytics/companies",
        "/analytics/locations",
        "/analytics/salary",
        "/analytics/jobs/trend",
        "/analytics/overview",
        "/pipeline/status",
        "/sources/status",
    }
    assert required.issubset(paths)


def test_settings_are_cloud_free():
    settings = get_settings()
    assert settings.database_url
    assert not hasattr(settings, "aws_region")
    assert not hasattr(settings, "s3_bucket")
    assert settings.scheduler_interval_minutes >= 1


def test_health_endpoint_exists():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code in {200, 503}
    if response.status_code == 200:
        assert response.json()["status"] == "ok"
        assert "database_url" not in response.text.lower()


def test_jobs_reject_invalid_pagination_and_filters():
    client = TestClient(app)
    assert client.get("/jobs?page=0").status_code == 422
    assert client.get("/jobs?page_size=101").status_code == 422
    assert client.get("/jobs?status=UNKNOWN").status_code == 422


def test_database_errors_are_structured_and_do_not_leak_details():
    class FailedDatabase:
        def query(self, *_args, **_kwargs):
            raise SQLAlchemyError("private connection string must not leak")

    def failing_db():
        yield FailedDatabase()

    app.dependency_overrides[get_db] = failing_db
    client = TestClient(app)
    try:
        response = client.get("/companies")
        assert response.json() == {
            "detail": {
                "code": "database_unavailable",
                "message": "The requested data is temporarily unavailable.",
            }
        }
        assert "private connection string" not in response.text
        assert response.status_code == 503
    finally:
        app.dependency_overrides.pop(get_db, None)
