"""Conservative deterministic gate; never a diagnostic classifier."""
RED_FLAGS = {"chest_pain", "syncope", "severe_breathlessness", "acute_injury", "abnormal_hr_with_discomfort"}
TEXT_FLAGS = ("胸痛", "胸口痛", "晕厥", "昏厥", "严重呼吸困难", "急性损伤", "异常心率并伴随不适", "chest pain", "fainted", "syncope", "severe shortness of breath", "acute injury")

def screen(profile: dict, checkin: dict | None = None, latched: str | None = None) -> dict:
    c = checkin or {}
    text = c.get("notes", "").lower()
    # Deliberately conservative: ambiguous/negated red-flag text requires clarification.
    if latched == "STOP_TRAINING" or RED_FLAGS.intersection(c.get("symptoms", [])) or any(s in text for s in TEXT_FLAGS):
        return {"status": "STOP_TRAINING", "reason": "报告或尚未解除的危险症状；停止训练。胸痛、晕厥或严重呼吸困难等请及时联系当地急救；急性损伤请及时就医。"}
    if c.get("pain", 0) > 0 or profile.get("injuries_or_limitations"):
        return {"status": "REVIEW_REQUIRED", "reason": "当前疼痛或具体运动限制需要先澄清适合的动作；暂不自动安排可能加重不适的普通处方。"}
    if profile.get("age") is None or not profile.get("safety_screen_complete"):
        return {"status": "NEEDS_SCREENING", "reason": "先确认年龄及运动风险筛查；身体测量与能力测试可缺失。"}
    if profile["age"] < 18:
        return {"status": "REVIEW_REQUIRED", "reason": "当前规则仅覆盖成人；未成年人需要合适的专业方案。"}
    warnings = []
    if profile.get("medical_conditions"):
        warnings.append("已记录健康情况。一般运动计划不替代疾病专项建议；结合自身感受调整，有条件时可咨询专业人员。就医或提交报告不是继续使用的前置条件。")
    return {"status": "OK", "reason": "未报告触发拦截的当前症状；健康史仅作提醒，不代表医学许可。", "warnings": warnings}
