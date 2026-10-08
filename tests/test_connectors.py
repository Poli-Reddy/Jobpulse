from app.connectors import ArbeitnowConnector, JobicyConnector
from app.http import http_session
from app.normalization import normalize_arbeitnow, normalize_jobicy


def test_jobicy_normalization():
    x={"id":1,"jobTitle":"Data Engineer","companyName":"Acme","jobGeo":"Remote","jobDescription":"<p>Python SQL AWS</p>","url":"https://jobicy.com/jobs/1","pubDate":"2026-10-01T00:00:00Z"}
    j=normalize_jobicy(x)
    assert j.source_job_id == "1"
    assert "Python" in j.skills


def test_arbeitnow_normalization():
    x={
        "slug": "backend-engineer",
        "company_name": "Acme",
        "title": "Backend Engineer",
        "location": "Remote",
        "description": "Python FastAPI SQL",
        "url": "https://www.arbeitnow.com/jobs/backend-engineer",
        "created_at": "2026-10-01T00:00:00Z",
    }
    j = normalize_arbeitnow(x)
    assert j.title == "Backend Engineer"
    assert "Python" in j.skills
    assert j.location == "Remote"


def test_connectors_retain_bad_records_without_stopping_the_batch(monkeypatch):
    payloads = [
        {
            "id": 1,
            "jobTitle": "Data Engineer",
            "companyName": "Acme",
            "url": "https://jobicy.com/jobs/1",
        },
        {"id": 2, "jobTitle": "", "companyName": "Acme", "url": "not a URL"},
    ]
    monkeypatch.setattr(
        "app.connectors.get_json",
        lambda *_args, **_kwargs: {"jobs": payloads},
    )

    records = JobicyConnector().fetch()

    assert len(records) == 2
    assert records[0].job is not None
    assert records[1].job is None
    assert records[1].error


def test_arbeitnow_empty_response_is_valid(monkeypatch):
    monkeypatch.setattr("app.connectors.get_json", lambda *_args, **_kwargs: {"data": []})
    assert ArbeitnowConnector().fetch() == []


def test_http_retry_policy_is_bounded_with_backoff():
    session = http_session()
    adapter = session.get_adapter("https://")
    assert adapter.max_retries.total == 2
    assert adapter.max_retries.backoff_factor > 0
    session.close()
