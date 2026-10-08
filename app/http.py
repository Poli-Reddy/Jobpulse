import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.config import get_settings

log = logging.getLogger(__name__)


def http_session() -> requests.Session:
    settings = get_settings()
    retry = Retry(
        total=max(0, settings.max_retries - 1),
        connect=max(0, settings.max_retries - 1),
        read=max(0, settings.max_retries - 1),
        status=max(0, settings.max_retries - 1),
        backoff_factor=settings.retry_backoff_seconds,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    session.headers.update({"User-Agent": "JobPulse/1.0 (+public job market analytics)"})
    return session


def get_json(url: str, params: dict | None = None):
    timeout = get_settings().request_timeout_seconds
    with http_session() as session:
        try:
            response = session.get(url, params=params, timeout=timeout)
        except requests.RequestException as exc:
            raise RuntimeError(
                f"public source request failed: {type(exc).__name__}"
            ) from exc
        if response.status_code >= 400:
            log.warning("Public source returned HTTP %s", response.status_code)
            raise RuntimeError(f"public source returned HTTP {response.status_code}")
        try:
            return response.json()
        except requests.exceptions.JSONDecodeError as exc:
            raise ValueError("public source returned invalid JSON") from exc
