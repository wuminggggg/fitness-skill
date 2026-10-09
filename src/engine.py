"""Orchestrates validated intake -> safety -> state -> target -> prescription."""
from datetime import date
from .validation import validate
from .intake import merge_profile
from .assessment import assess
from .safety import screen
from .trend_analysis import analyze
from .adaptation import adapt, change, elapsed
from .prescription import prescribe
from .goal_engine import evaluate_goal, forecast
from .state_manager import StateManager

class FitnessEngine:
    def __init__(self, repository: StateManager): self.repo = repository

    def update_profile(self, update: dict) -> dict:
        with self.repo.transaction() as data:
            data["profile"] = merge_profile(data["profile"], update)
            data["audit"].append({"event":"profile_update", "fields":sorted(update)})
            return data["profile"]

    def checkin(self, checkin: dict) -> dict:
        validate("daily_checkin", checkin)
        with self.repo.transaction() as data:
            if data["state"] and checkin["date"] < data["state"]["last_evaluated"]:
                raise ValueError("Backdated checkins require explicit replay; ordinary CLI only accepts current/future dates")
            old = next((c for c in data["checkins"] if c["date"] == checkin["date"]), {})
            merged = {**old, **checkin}
            data["checkins"] = [c for c in data["checkins"] if c["date"] != checkin["date"]] + [merged]
            gate = screen(data["profile"], merged, data["safety_latch"])
            if gate["status"] == "STOP_TRAINING": data["safety_latch"] = "STOP_TRAINING"
            data["audit"].append({"event":"checkin", "date":checkin["date"], "safety":gate})
            return gate

    def record(self, record: dict) -> dict:
        validate("workout_record", record)
        with self.repo.transaction() as data:
            plan = next((p for p in data["plans"] if p["plan_id"] == record["plan_id"] and p["date"] == record["date"]), None)
            if not plan: raise ValueError("Record must reference an existing plan on the same date")
            if not plan["targets"]["active_minutes"]: raise ValueError("Cannot log a workout against a rest/blocked plan")
            if data["state"] and record["date"] < data["state"]["last_evaluated"]: raise ValueError("Backdated records require explicit replay")
            if (record.get("performance_score") is None) != (record.get("performance_test_id") is None): raise ValueError("Performance score and standardized test ID must be supplied together")
            load = record["duration_minutes"] * record["rpe"] if record.get("rpe") is not None else None
            if "training_load" in record and record["training_load"] != load: raise ValueError("training_load is derived, not caller-controlled")
            result = {**record,"training_load":load}
            existing = next((r for r in data["records"] if r["date"] == result["date"]), None)
            if existing:
                if existing == result: return existing
                raise ValueError("Record already exists; conflicting edits require explicit correction workflow")
            data["records"].append(result)
            data["audit"].append({"event":"workout_record", "date":result["date"], "training_load":load})
            return result

    def plan(self, day: str, indoors: bool = False) -> dict:
        date.fromisoformat(day)
        with self.repo.transaction() as data:
            profile = data["profile"]
            previous_state = data["state"]
            if previous_state and day < previous_state["last_evaluated"]: raise ValueError("Plans must advance chronologically")
            checkins = sorted((c for c in data["checkins"] if c["date"] <= day), key=lambda c:c["date"])
            latest = checkins[-1] if checkins else {}
            # Red flags remain latched. Recent recovery is not treated as current forever.
            gate = screen(profile, latest, data["safety_latch"])
            if gate["status"] == "STOP_TRAINING": data["safety_latch"] = "STOP_TRAINING"
            cached = next((p for p in data["plans"] if p["date"] == day), None)
            trends = analyze(checkins, data["records"], data["plans"], day)
            previous_plan = max((p for p in data["plans"] if p["date"] < day), key=lambda p:p["date"], default=None)
            assessment = assess(profile, trends, latest)
            cap = min([profile[k] for k in ("available_minutes","preferred_session_minutes") if profile.get(k) is not None] or [15])
            if previous_state:
                state = {**previous_state, **{k:assessment[k] for k in ("body","activity","fitness","recovery","adherence","confidence")}}
            else:
                state = {**assessment,"phase_since":day,"last_adjusted":None,"baseline_minutes":min(12, cap),"last_evaluated":day}
            last_plan_event = max((i for i, event in enumerate(data["audit"]) if event["event"] == "plan" and event["date"] == day), default=-1)
            dirty = any(event["event"] in ("checkin", "profile_update") for event in data["audit"][last_plan_event + 1:])
            if cached and not dirty and gate["status"] == "OK":
                # Do not compound daily adjustments; retain targets, but enforce tighter availability.
                if cached["targets"]["active_minutes"] <= cap and cached["safety_status"] == "OK":
                    target = {k:v for k,v in cached.items() if k != "prescription"}
                    prescription = prescribe(target,profile,cached,indoors)
                    if prescription != cached["prescription"]:
                        adjustment = change("prescription", "按环境替换动作，保留当天指标并保存替换结果。", cached["prescription"], prescription)
                        target["changes"] = [*target["changes"], adjustment]
                        cached.update(target)
                        cached["prescription"] = prescription
                        data["audit"].append({"event":"prescription_update", "date":day, "changes":[adjustment]})
                    validate("fitness_state",state)
                    data["state"] = state
                    return {"target":target,"prescription":prescription,"state":state,"goal":evaluate_goal(profile),"forecast":forecast(profile,checkins,trends,day),"safety":gate}
            if gate["status"] == "OK":
                state, changes = adapt(state,previous_plan,checkins,trends,[r for r in data["records"] if r["date"] < day],day)
            else:
                changes = [change("safety" if gate["status"] != "OK" else "availability",gate["reason"] if gate["status"] != "OK" else "当前时间上限缩短，重新约束本日处方。",cached["targets"]["active_minutes"] if cached else None,0 if gate["status"] != "OK" else cap)]
            count = profile.get("max_sessions_per_week")
            count = 3 if count is None else count
            allowed = [d for d in (0,3,5,1,4,2,6) if d not in profile.get("schedule_constraints", [])][:count]
            scheduled = date.fromisoformat(day).weekday() in allowed
            minutes = min(cap, state["baseline_minutes"]) if scheduled and gate["status"] == "OK" else 0
            if latest and elapsed(day,latest["date"]) <= 2 and latest.get("sleep_hours") is not None and latest["sleep_hours"] < 6 and state["phase"] != "DELOAD":
                minutes *= .9
                changes.append(change("today_minutes","单次短睡眠仅对本日保守减量10%，不重置长期基线。",min(cap,state["baseline_minutes"]),minutes))
            minutes = round(minutes,2)
            mobility = round(min(4,minutes*.3),2)
            strength = round((minutes-mobility)*.5,2) if minutes >= 10 else 0
            if profile.get("primary_goal") == "endurance": strength = round(strength*.6,2)
            if profile.get("primary_goal") == "muscle_gain": strength = round((minutes-mobility)*.65,2) if minutes >= 10 else 0
            if previous_plan and elapsed(day,previous_plan["date"]) == 1 and previous_plan["targets"]["strength_minutes"] > 0: strength = 0
            cardio = round(minutes-mobility-strength,2)
            steps = trends["7"]["steps"]["mean"]
            if steps is None: steps = profile.get("daily_steps")
            if gate["status"] != "OK": steps = None
            rpe = 3  # Only time progresses in v1; phase changes must not also raise intensity.
            target = {"date":day,"plan_id":f"plan-{day}","targets":{"steps":round(steps) if steps is not None else None,"active_minutes":minutes,"cardio_minutes":cardio,"strength_minutes":strength,"mobility_minutes":mobility,"intensity":"low"},"rpe_target":rpe if minutes else 0,"training_load_target":round(minutes*rpe,2),"phase":state["phase"],"safety_status":gate["status"],"changes":changes}
            if not scheduled and gate["status"] == "OK": target["changes"].append(change("rest_day","固定周日程安排休息。",None,0))
            if previous_plan:
                for key, new in target["targets"].items():
                    old = previous_plan["targets"].get(key)
                    if old != new:
                        explanation = "遵循本日安全状态、固定周日程、可用时间和已调整基线；热身放松包含在总时长内。"
                        if key == "strength_minutes" and strength == 0 and minutes:
                            explanation = "连续日避免重复力量刺激，或本日时长不足10分钟；保留轻有氧与活动。"
                        if key == "steps": explanation = "沿用最近7天实测平均步数；无记录时沿用建档基线，不额外叠加步数负荷。"
                        target["changes"].append(change("targets." + key,explanation,old,new))
            prescription = prescribe(target,profile,cached or previous_plan,indoors)
            state["last_evaluated"] = day
            validate("fitness_state",state)
            validate("workout_target",target)
            data["state"] = state
            data["plans"] = [p for p in data["plans"] if p["date"] != day] + [{**target,"prescription":prescription}]
            data["audit"].append({"event":"plan","date":day,"previous_plan_id":previous_plan["plan_id"] if previous_plan else None,"changes":changes})
            return {"target":target,"prescription":prescription,"state":state,"goal":evaluate_goal(profile),"forecast":forecast(profile,checkins,trends,day),"safety":gate}
