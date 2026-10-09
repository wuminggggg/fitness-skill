"""Stable movement templates constrained by the deterministic time/intensity budget."""
from copy import deepcopy
from .validation import validate

MOVEMENTS = {
    "cardio": ["平地步行", "室内低冲击踏步"],
    "squat": ["椅子坐站", "浅幅徒手深蹲"],
    "push": ["墙壁俯卧撑", "高位支撑俯卧撑"],
    "hip": ["臀桥", "站姿髋后伸"],
    "mobility": ["舒适范围肩踝活动", "轻柔全身活动"],
}

def prescribe(target: dict, profile: dict, previous_plan: dict | None = None, indoors: bool = False) -> dict:
    validate("workout_target", target)
    if target["safety_status"] != "OK": return {"blocks": [], "reason": "安全拦截，不生成训练处方。"}
    t = target["targets"]
    if not t["active_minutes"]: return {"blocks": [], "reason": "计划休息日，无强制训练。"}
    dislikes = profile.get("exercise_dislikes", [])
    def choose(category):
        options = MOVEMENTS[category]
        if category == "cardio" and indoors: options = ["室内低冲击踏步"]
        options = [s for s in options if not any(d.lower() in s.lower() for d in dislikes)]
        if not options: raise ValueError(f"No suitable movement for {category}; clarify preferences")
        # A plateau changes only the cardio variant, preserving duration and RPE.
        if category == "cardio" and target["phase"] == "PLATEAU" and (previous_plan or {}).get("phase") != "PLATEAU" and not indoors:
            old = next((b["movement"] for b in (previous_plan or {}).get("prescription",{}).get("blocks",[]) if b["category"] == "cardio"),None)
            alternatives = [s for s in options if s != old]
            if alternatives: return alternatives[0]
        # Keep the previous template if still compatible.
        for block in (previous_plan or {}).get("prescription", {}).get("blocks", []):
            if block.get("category") == category and block["movement"] in options: return block["movement"]
        return options[0]
    blocks = []
    mobility = t["mobility_minutes"]
    for label in ("热身", "放松"):
        blocks.append({"category":"mobility", "movement":choose("mobility"), "label":label,"minutes":mobility / 2,"instructions":"缓慢活动，无痛范围；计入总时间。"})
    if t["cardio_minutes"]:
        blocks.insert(1, {"category":"cardio", "movement":choose("cardio"), "minutes":t["cardio_minutes"], "instructions":f"整体目标RPE {target['rpe_target']}，能舒适交谈；不适即停。"})
    if t["strength_minutes"]:
        # Fixed slots include rest; never append unbudgeted sets to a 20-minute plan.
        slot = t["strength_minutes"] / 3
        for category in ("squat", "push", "hip"):
            blocks.insert(-1, {"category":category,"movement":choose(category),"minutes":slot,"sets":1,"reps_range":[4,8],"instructions":"慢速4–8次，剩余时段休息；无需做到力竭。时间到即停。"})
    return {"blocks":blocks,"total_minutes":sum(b["minutes"] for b in blocks),"rpe_target":target["rpe_target"],"reason":"沿用基础动作模板；每个时段含休息，热身放松计入总时长。"}

def substitute(prescription: dict, category: str, movement: str) -> dict:
    if movement not in MOVEMENTS.get(category, []): raise ValueError("Replacement is outside the vetted category")
    result = deepcopy(prescription)
    matches = [b for b in result.get("blocks", []) if b["category"] == category]
    if not matches: raise ValueError("No matching block")
    for block in matches: block["movement"] = movement
    result["reason"] = "仅替换同类动作；保持时段和目标RPE。实际负荷由训练后RPE校验。"
    return result
