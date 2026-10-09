"""Calendar windows, observed denominators, no fabricated missing observations."""
from datetime import date, timedelta
from statistics import mean

METRICS = ("weight_kg", "steps", "duration_minutes", "training_load", "rpe", "fatigue", "completion")

def window(rows: list[dict], day: str, days: int) -> list[dict]:
    end = date.fromisoformat(day)
    start = end - timedelta(days=days - 1)
    return sorted((r for r in rows if start <= date.fromisoformat(r["date"]) <= end), key=lambda r: r["date"])

def slope(rows: list[dict], key: str) -> float | None:
    observed = [r for r in rows if r.get(key) is not None]
    if len(observed) < 3: return None
    xs = [date.fromisoformat(r["date"]).toordinal() for r in observed]
    ys = [r[key] for r in observed]
    denominator = sum((x - mean(xs)) ** 2 for x in xs)
    return sum((x - mean(xs)) * (y - mean(ys)) for x, y in zip(xs, ys)) / denominator if denominator else None

def analyze(checkins: list[dict], records: list[dict], plans: list[dict], day: str) -> dict:
    merged = {c["date"]: dict(c) for c in checkins}
    for r in records:
        # Feedback in records can be null; never erase a checkin with a null.
        merged.setdefault(r["date"], {"date": r["date"]}).update({k: v for k, v in r.items() if v is not None})
    result = {}
    for days in (7, 14, 30):
        rows = window(list(merged.values()), day, days)
        summary = {}
        for key in METRICS:
            values = [r[key] for r in rows if r.get(key) is not None]
            summary[key] = {"mean": mean(values) if values else None, "count": len(values), "slope_per_day": slope(rows, key)}
        # Today's uncompleted plan is not yet overdue; missing feedback stays unknown.
        scheduled = [p for p in window(plans, day, days) if p["date"] < day and p["targets"]["active_minutes"] > 0]
        observed = [r for r in window(records, day, days) if r["date"] < day and any(p["date"] == r["date"] for p in scheduled)]
        summary["adherence"] = {"scheduled": len(scheduled), "reported": len(observed), "coverage": len(observed) / len(scheduled) if scheduled else 0,
            "completion_rate": mean(r["completion"] for r in observed) if observed else None}
        summary["training_load"]["total"] = sum(r.get("training_load", 0) or 0 for r in rows)
        result[str(days)] = summary
    return result
