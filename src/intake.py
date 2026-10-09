"""Incremental intake; unknown values stay unknown."""
from .validation import validate

STAGES = [
    ("safety", ["age", "safety_screen_complete", "medical_conditions"]),
    ("practical", ["primary_goal", "available_minutes", "max_sessions_per_week"]),
    ("baseline", ["height_cm", "weight_kg", "daily_steps"]),
    ("preferences", ["equipment", "schedule_constraints", "exercise_dislikes"]),
    ("capacity", ["training_experience", "pushups_max", "running_level"]),
]

def merge_profile(previous: dict, update: dict) -> dict:
    result = {**previous, **update}
    return validate("user_profile", result)

def next_questions(profile: dict) -> dict:
    for stage, fields in STAGES:
        missing = [f for f in fields if profile.get(f) is None]
        if missing:
            return {"stage": stage, "fields": missing[:3], "optional": stage not in ("safety", "practical")}
    return {"stage": "ready", "fields": [], "optional": True}
