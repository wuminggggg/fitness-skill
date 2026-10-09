# 安全拦截与恢复

风险状态与训练阶段分离：OK、NEEDS_SCREENING、REVIEW_REQUIRED、STOP_TRAINING。任何非OK状态输出空处方及零训练分钟，不生成替代训练绕过拦截。

结构化红旗：chest_pain、syncope、severe_breathlessness、acute_injury、abnormal_hr_with_discomfort。安全模块也检查少量中英文红旗原文，作为结构化提取遗漏的后备。正常酸痛不等于急性损伤，疼痛使用单独pain字段并暂停普通处方。

胸痛、晕厥、严重呼吸困难等可能需要紧急医疗帮助，应停止训练并联系当地急救；急性损伤及时就医。参考：[美国心脏协会心脏病发作警示症状](https://www.heart.org/en/health-topics/heart-attack/warning-signs-of-a-heart-attack)；访问日期2026-10-09。代码不诊断症状病因。

STOP_TRAINING持久锁定，不因下一天症状字段为空而清除。v1没有自助解锁功能；恢复需要独立的专业评估/人工治理流程，不允许代理编辑JSON解锁。medical_conditions非空不再触发REVIEW_REQUIRED；引擎返回OK并附带warnings，继续一般运动规划，不要求先取得医生许可。年龄<18、当前疼痛或injuries_or_limitations仍按相应门禁处理；布尔筛查标志不能豁免当前危险症状。

关键词不能可靠理解否定、既往史和所有自然语言：例如“没有胸痛”也可能保守触发停训。因此问答先区分当前/历史/否定，填写结构化字段；原文含红旗且含义不明时优先暂停和澄清，不能宣称文本分类完备。病情字段不能由LLM默认为空以绕过门禁。


## 健康史提醒与当前症状分开

健康史仅记录用户已提供的信息，不凭名称推断疾病轻重。Agent简短说明提醒后继续收集目标、时间与频率，不提供“先看医生才能继续”的二选一，也不对生活习惯作未经证实的归因。引擎仍使用一般低强度起始规则，不声称提供疾病专项治疗、术后或孕期康复方案。

参考：[NIDDK关于非酒精性脂肪肝的治疗说明](https://www.niddk.nih.gov/health-information/liver-disease/nafld-nash/treatment)指出身体活动即使未减重也可能有益；因此仅凭“脂肪肝”名称一律禁止生成一般运动计划并不合适。该资料不等于所有疾病和状态均可使用同一处方。访问日期2026-10-09。

旧版本仅因健康史产生的REVIEW_REQUIRED不是持久停训锁；更新后再次生成计划即按新规则评估，无需删档或篡改疾病字段。真正由危险症状产生的STOP_TRAINING锁保持有效。
