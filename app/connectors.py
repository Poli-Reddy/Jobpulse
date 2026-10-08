import logging
from dataclasses import dataclass
from typing import Any

from app.config import get_settings
from app.http import get_json
from app.normalization import normalize_arbeitnow, normalize_jobicy
from app.schemas import NormalizedJob

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SourceRecord:
    payload: dict[str, Any]
    job: NormalizedJob | None
    error: str | None = None


def _records(name: str, payloads: Any, normalizer) -> list[SourceRecord]:
    if not isinstance(payloads, list):
        raise ValueError(f"{name} response jobs field must be a list")
    records = []
    for index, payload in enumerate(payloads):
        if not isinstance(payload, dict):
            records.append(
                SourceRecord(
                    payload={"received_value": repr(payload)[:1000]},
                    job=None,
                    error=f"record {index} is not a JSON object",
                )
            )
            continue
        try:
            records.append(SourceRecord(payload=payload, job=normalizer(payload)))
        except (TypeError, ValueError) as exc:
            records.append(SourceRecord(payload=payload, job=None, error=str(exc)[:1000]))
    return records


class JobicyConnector:
    name = "jobicy"

    def fetch(self) -> list[SourceRecord]:
        settings = get_settings()
        params = {"count": settings.jobicy_count}
        if settings.jobicy_geo:
            params["geo"] = settings.jobicy_geo
        if settings.jobicy_industry:
            params["industry"] = settings.jobicy_industry
        data = get_json(settings.jobicy_base_url, params)
        if not isinstance(data, dict):
            raise ValueError("Jobicy response must be a JSON object")
        records = _records(self.name, data.get("jobs"), normalize_jobicy)
        if not records:
            log.warning("%s returned an empty jobs list", self.name)
        return records

class ArbeitnowConnector:
    name = "arbeitnow"

    def fetch(self) -> list[SourceRecord]:
        data = get_json(get_settings().arbeitnow_base_url)
        if isinstance(data, list):
            payloads = data
        elif isinstance(data, dict):
            payloads = data.get("data")
        else:
            raise ValueError("Arbeitnow response must be a JSON object or list")
        records = _records(self.name, payloads, normalize_arbeitnow)
        if not records:
            log.warning("%s returned an empty jobs list", self.name)
        return records


def enabled_connectors():
    settings = get_settings()
    connectors = []
    if settings.jobicy_enabled:
        connectors.append(JobicyConnector())
    if settings.arbeitnow_enabled:
        connectors.append(ArbeitnowConnector())
    return connectors
