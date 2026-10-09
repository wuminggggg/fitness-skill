"""Auditable state transitions and rate-limited deterministic adaptation."""
from copy import deepcopy
from datetime import date, timedelta
from statistics import mean
from .trend_analysis import window

def elapsed(day: str, previous: str | None) -> int:
    return (date.fromisoformat(day) - date.fromisoformat(previous)).days if previous else 9999

def change(name, reason, old, new) -> dict:
    return {"change": name, "reason": reason, "previous_value": old, "new_value": new}

def plateau(records: list[dict], day: str) -> bool:
    rows = [r for r in window(records, day, 21) if r.get("performance_score") is not None and r.get("performance_test_id")]
    groups = {}
    for r in rows: groups.setdefault(r["performance_test_id"], []).append(r)
    for group in groups.values():
        bins = [[r["performance_score"] for r in group if i * 7 <= elapsed(day, r["date"]) < (i + 1) * 7] for i in range(3)]
        if all(len(b) >= 2 for b in bins):
            values = [mean(b) for b in bins]
            if min(values) > 0 and (max(values) - min(values)) / min(values) <= .02: return True
    return False

def adapt(previous_state: dict, previous_plan: dict | None, recent_feedback: list[dict], trend_data: dict,
          records: list[dict], day: str) -> tuple[dict, list[dict]]:
    state = deepcopy(previous_state)
    changes = []
    phase, baseline = state["phase"], state["baseline_minutes"]
    recent = window(recent_feedback, day, 7)
    fresh = recent and elapsed(day, recent[-1]["date"]) <= 2
    latest = recent[-1] if fresh else {}
    tired = [c for c in recent if (c.get("fatigue") or 0) >= 7 and c.get("sleep_hours") is not None and c["sleep_hours"] < 6]
    scores = [r["completion"] for r in window(records, day, 7)]
    declining = len(scores) >= 3 and scores[-1] < scores[-2] < scores[-3]
    persistent = len(tired) >= 3 and declining
    high = (latest.get("fatigue") or 0) >= 8 or max((latest.get("soreness") or {}).values(), default=0) >= 8
    def transition(new_phase, reason):
        nonlocal phase
        changes.append(change("phase", reason, phase, new_phase))
        phase = new_phase
        state["phase_since"] = day
    if (high or persistent) and phase != "DELOAD":
        transition("DELOAD", "高疲劳/严重酸痛，或多日短睡眠、疲劳并伴连续完成率下降。")
        state["baseline_minutes"] = round(baseline * .75, 2)
        state["last_adjusted"] = day
        changes.append(change("baseline_minutes", "恢复优先，减量25%；进入DELOAD仅应用一次。", baseline, state["baseline_minutes"]))
    elif phase == "DELOAD":
        recovered = [c for c in recent if c.get("fatigue") is not None and c["fatigue"] <= 4 and (c.get("sleep_hours") or 0) >= 7 and max((c.get("soreness") or {}).values(), default=0) <= 4]
        if fresh and len(recovered) >= 3 and latest in recovered and elapsed(day, state["phase_since"]) >= 7 and not high and not persistent:
            transition("PROGRESS", "减量至少7天且至少3次恢复良好记录；以减量后的基线恢复渐进。")
    elif phase == "INIT" and records:
        transition("ADAPTATION", "已完成首次反馈，进入习惯与动作适应期。")
    elif phase == "ADAPTATION" and elapsed(day, state["phase_since"]) >= 14 and len(window(records, day, 30)) >= 4 and state["confidence"] >= .5:
        transition("PROGRESS", "适应至少14天、至少4次训练记录且数据置信度达到0.5。")
    elif phase == "PROGRESS" and trend_data["14"]["adherence"]["coverage"] >= .85 and (trend_data["14"]["adherence"]["completion_rate"] or 0) >= .85 and elapsed(day, state["phase_since"]) >= 21 and plateau([r for r in records if r["date"] >= state["phase_since"]], day):
        transition("PLATEAU", "本轮PROGRESS至少21天；仅用进入本轮后同一测试的3周数据（每周至少2次），变化不超过2%，复评刺激。")
    elif phase == "PLATEAU" and elapsed(day, state["phase_since"]) >= 7:
        transition("DELOAD", "平台复评7天后安排减量周期，再逐步恢复。")
        state["baseline_minutes"] = round(baseline * .75, 2)
        state["last_adjusted"] = day
        changes.append(change("baseline_minutes", "平台后的计划减量25%。", baseline, state["baseline_minutes"]))
    adherence = trend_data["14"]["adherence"]
    avg_rpe = trend_data["14"]["rpe"]["mean"]
    # Require recovery and feedback coverage; absent feedback is not success.
    recovery_ok = fresh and latest.get("fatigue") is not None and latest["fatigue"] <= 4 and (latest.get("sleep_hours") or 0) >= 7 and max((latest.get("soreness") or {}).values(), default=0) <= 4
    eligible = phase == "PROGRESS" and not changes and previous_plan is not None and adherence["reported"] >= 4 and adherence["coverage"] >= .85 and (adherence["completion_rate"] or 0) >= .85 and avg_rpe is not None and avg_rpe <= 6 and trend_data["14"]["rpe"]["count"] >= 4 and recovery_ok and elapsed(day, state.get("last_adjusted")) >= 7
    if eligible:
        factor = 1.05 if state["confidence"] >= .6 else 1.02
        state["baseline_minutes"] = round(min(180, baseline * factor), 2)
        state["last_adjusted"] = day
        changes.append(change("baseline_minutes", "近14天执行率与反馈覆盖充分、RPE≤6且恢复良好；仅增加时长。", baseline, state["baseline_minutes"]))
    state["phase"] = phase
    state["last_evaluated"] = day
    if not changes: changes.append(change("hold", "维持前次基线；数据不足、尚未到调整间隔或未满足进阶条件。", baseline, baseline))
    return state, changes

def progress_dose(dose: dict, mode: str, cap: float = .05) -> dict:
    """One-variable candidate for coach-selected progression; no forced discrete jumps.

    Proxy = minutes for time; sets*reps*difficulty_factor otherwise.
    A request too coarse for the cap is returned unchanged, with a reason.
    """
    if mode not in ("time", "reps", "sets", "difficulty"): raise ValueError("Unknown progression mode")
    if not 0 < cap <= .05: raise ValueError("Progression cap must be in (0, .05]")
    for key in ("minutes", "sets", "reps", "difficulty_factor"):
        if key not in dose or isinstance(dose[key], bool) or not isinstance(dose[key], (int,float)) or not 0 < dose[key] < 10000:
            raise ValueError("Positive finite dose values required")
    candidate = deepcopy(dose)
    key = {"time":"minutes", "reps":"reps", "sets":"sets", "difficulty":"difficulty_factor"}[mode]
    if mode == "time": candidate[key] *= 1 + cap
    elif mode in ("sets", "reps"): candidate[key] += 1
    else:
        factor = dose.get("next_difficulty_factor")
        if not isinstance(factor, (int,float)) or not dose["difficulty_factor"] < factor < 100: raise ValueError("Calibrated next difficulty factor required")
        candidate[key] = factor
    ratio = candidate[key] / dose[key]
    if ratio > 1 + cap + 1e-9:
        return {"dose": dose, "change": change(mode, "离散增量超过负荷上限，保留原剂量；改用更细时间进阶。", dose[key], dose[key])}
    return {"dose": candidate, "change": change(mode, "仅改变一个变量，代理负荷增幅不超过上限；难度系数需校准。", dose[key], candidate[key])}
