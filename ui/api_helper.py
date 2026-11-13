"""api_helper.py
Utility to guarantee that any payload sent to the FastAPI backend contains a proper
JSON object for fields that expect a dict (e.g. the `src` field used by some
endpoints)."""
import json
from typing import Any, Dict

def ensure_dict(payload: Any) -> Dict:
    """Return a dict representation of ``payload``.

    - If ``payload`` is already a ``dict`` it is returned unchanged.
    - If it is a JSON string, it is parsed via ``json.loads``.
    - Otherwise a ``ValueError`` is raised so the caller can surface a clear
      error message before the request is sent.
    """
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        try:
            parsed = json.loads(payload)
            if not isinstance(parsed, dict):
                raise ValueError("Parsed JSON is not an object.")
            return parsed
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON string supplied: {exc}") from exc
    raise ValueError(f"Payload must be a dict or JSON string, got {type(payload)}")
