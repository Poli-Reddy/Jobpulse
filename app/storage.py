import hashlib
import json
from typing import Any


def payload_hash(payload: dict[str, Any]) -> str:
    canonical_payload = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    )
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()
