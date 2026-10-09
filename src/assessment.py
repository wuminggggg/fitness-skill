"""Descriptive assessment with explicit missingness, not a medical diagnosis."""
from .validation import validate

def assess(profile: dict, trends: dict | None = None, checkin: dict | None = None) -> dict:
    validate("user_profile", profile)
    t, c = trends or {}, checkin or {}
    def metric(days, key, field="mean"):
        return t.get(str(days), {}).get(key, {}).get(field)
    height, weight = profile.get("height_cm"), profile.get("weight_kg")
    bmi = round(weight / (height / 100) ** 2, 2) if weight and height else None
    known = sum(profile.get(k) is not None for k in ("age", "height_cm", "weight_kg", "daily_steps", "training_experience"))
    observed = sum(min(metric(30, k, "count") or 0, 14) / 14 for k in ("weight_kg", "rpe", "fatigue", "completion")) / 4
    confidence = round(min(.9, .15 + .03 * known + .6 * observed), 3)
    pushups = profile.get("pushups_max")
    running = {"none": .1, "walk": .2, "run_walk": .4, "continuous": .6}
    return {
        "body": {"bmi": bmi, "weight_trend_7d": metric(7, "weight_kg", "slope_per_day"), "weight_trend_30d": metric(30, "weight_kg", "slope_per_day"), "estimated_body_fat": None},
        "activity": {"activity_level": "unknown" if profile.get("daily_steps") is None else ("low" if profile["daily_steps"] < 5000 else "active"), "weekly_training_load": metric(7, "training_load", "total"), "step_average_7d": metric(7, "steps")},
        "fitness": {"cardio_level": running.get(profile.get("running_level")), "strength_level": min(1, pushups / 40) if pushups is not None else None, "mobility_level": None},
        "recovery": {"fatigue": c.get("fatigue"), "sleep_quality": c.get("sleep_quality"), "soreness": c.get("soreness")},
        "adherence": {"completion_rate_7d": metric(7, "adherence", "completion_rate"), "completion_rate_14d": metric(14, "adherence", "completion_rate")},
        "confidence": confidence, "phase": "INIT"
    }
