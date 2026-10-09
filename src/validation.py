"""One validation boundary for CLI, engine and persisted inputs."""
import json
import math
from pathlib import Path
from jsonschema import Draft202012Validator, FormatChecker

SCHEMAS = Path(__file__).resolve().parents[1] / "schemas"

def validate(kind: str, value: dict) -> dict:
    def finite(v):
        if isinstance(v, float) and not math.isfinite(v):
            raise ValueError("Non-finite numbers are not accepted")
        if isinstance(v, dict):
            for item in v.values(): finite(item)
        if isinstance(v, list):
            for item in v: finite(item)
    finite(value)
    schema = json.loads((SCHEMAS / f"{kind}.json").read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(value), key=lambda e: str(e.path))
    if errors:
        raise ValueError("; ".join(f"{'.'.join(map(str, e.path)) or kind}: {e.message}" for e in errors))
    return value
