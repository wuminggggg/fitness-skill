"""Goal plausibility and bounded trend extrapolation; no promised deadline."""
from datetime import date
import math
from .trend_analysis import window, slope

def evaluate_goal(profile: dict) -> dict:
    current, target = profile.get("weight_kg"), profile.get("target_weight_kg")
    result = {"primary_goal": profile.get("primary_goal") or "general_fitness", "suggested_weeks_range": None, "reason": "先建立可持续运动习惯，目标日期不是强制期限。"}
    if current and target and target < current:
        # Product heuristic, not a personalized medical weight-loss prescription.
        result["suggested_weeks_range"] = [math.ceil((current - target) / (current * .005)), math.ceil((current - target) / (current * .0025))]
        weeks = profile.get("desired_duration_weeks")
        if weeks and weeks < result["suggested_weeks_range"][0]: result["reason"] = "期望期限超出保守规划假设；建议更长时间，并根据真实趋势复评。"
    if target and profile.get("height_cm") and target / (profile["height_cm"] / 100) ** 2 < 18.5:
        result.update(suggested_weeks_range=None, reason="目标体重偏低；不自动追求该体重目标，需专业评估。")
    return result

def forecast(profile: dict, checkins: list[dict], trends: dict, day: str) -> dict:
    result = {"target_weight": profile.get("target_weight_kg"), "estimated_weeks_remaining": None, "estimated_weeks_range": None, "confidence": 0.0, "reason": "有效趋势不足，暂不预测。"}
    rows = [r for r in window(checkins, day, 30) if r.get("weight_kg") is not None]
    if not result["target_weight"] or len(rows) < 7: return result
    if (date.fromisoformat(rows[-1]["date"]) - date.fromisoformat(rows[0]["date"])).days < 14: return result
    if evaluate_goal(profile)["reason"].startswith("目标体重偏低"): return result
    delta = result["target_weight"] - rows[-1]["weight_kg"]
    s = slope(rows, "weight_kg")
    adherence = trends["14"]["adherence"]
    activity = trends["14"]["duration_minutes"]["mean"]
    if abs(delta) < .2:
        return {**result, "estimated_weeks_remaining": 0, "reason": "最近记录已接近目标；以持续趋势复核。"}
    if s is None or abs(s) < .01 or delta * s <= 0 or adherence["coverage"] < .75 or activity is None: return result
    weeks = delta / s / 7
    if weeks > 156: return result
    confidence = round(min(.8, len(rows) / 30 * .8) * adherence["coverage"] * (adherence["completion_rate"] or 0), 2)
    return {**result, "estimated_weeks_remaining": round(weeks, 1), "estimated_weeks_range": [round(weeks * .7, 1), round(weeks * 1.5, 1)], "confidence": confidence, "reason": "基于近30天体重斜率，且有活动与执行记录；仅为不确定的趋势外推。"}
