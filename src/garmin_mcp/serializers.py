"""Serialize garth dataclasses and Pydantic models to JSON-friendly dicts."""

import dataclasses
from datetime import date, datetime
from typing import Any


def to_jsonable(obj: Any) -> Any:
    """Recursively convert objects to JSON-serializable form (dict/list/str/int/float/bool)."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, list):
        return [to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    # Pydantic v2 dataclass / BaseModel
    if hasattr(obj, "model_dump"):
        return to_jsonable(obj.model_dump())
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {
            f.name: to_jsonable(getattr(obj, f.name))
            for f in dataclasses.fields(obj)
        }
    return obj
