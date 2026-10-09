# fitness-skill ｜ 长期自适应运动系统

**Long-term Adaptive Fitness System**

一个面向个人的、可长期维护的运动档案与训练处方引擎。它把人当作持续变化的系统来对待：先建档，再给每日指标，然后根据你的反馈和恢复趋势连续调整，而不是每天随机甩一份训练表。

A personal, long-horizon fitness archive and training prescription engine. It treats you as a system that keeps changing: build a profile first, then issue daily targets, then adapt continuously to your feedback and recovery trend — instead of throwing a random workout at you every day.

[中文](#中文) ｜ [English](#english)

---

## 中文

### 这是什么

fitness-skill 是一个纯 Python 的本地引擎，配合对话代理使用。它负责维护一份长期个人运动档案，按天生成抽象训练指标（时长、强度、负荷、阶段），再在时间预算内安排具体动作，并根据你回填的完成度、RPE、疲劳、睡眠和酸痛做确定性调整。

它不是在替你训练，也不做医学判断。它是一个把「记录—评估—处方—反馈—调整」这条闭环跑稳的工程系统。

### 主要特性

1. 分阶段建档。按安全、目标、基线、偏好、能力五段收信息，每轮最多三个问题；可选测量允许未知，不逼问，不要求极限测试。
2. 每日闭环。读取状态与原计划，输出抽象指标和动作处方；训练后记录完成比例、实际分钟、整体 RPE 与恢复反馈，下一次计划由上一状态和规则推导，并给出变化原因与前后值。
3. 确定性调整。进阶在满足条件时最多每 7 天增加 5% 时长，低数据置信度时为 2%；高疲劳触发一次 25% 减量；阶段依次覆盖 INIT、ADAPTATION、PROGRESS、PLATEAU、DELOAD。
4. 独立安全门禁。风险状态与训练阶段分离，危险症状触发持久停训锁，非 OK 状态一律输出空处方，不生成替代训练绕过拦截。
5. 原子状态。每个数据目录一份 snapshot.json，写入锁加修订号防止并发覆盖；遇到损坏或冲突不自动重置。

### 目录结构

```
fitness-skill/
├─ SKILL.md                 技能指令（给对话代理看的）
├─ README.md                本文件
├─ README.zh-CN.md          详细使用说明（中文）
├─ requirements.txt         运行依赖（仅 jsonschema）
├─ src/                     业务代码
│  ├─ cli.py                命令行入口
│  ├─ engine.py             协调各模块，保持状态一致
│  ├─ intake.py             分阶段字段提示与档案合并
│  ├─ assessment.py         描述性评估与数据充足度
│  ├─ goal_engine.py        目标合理性检查与趋势预测
│  ├─ adaptation.py         阶段、进阶、减量、恢复规则
│  ├─ prescription.py       时间预算内动作安排与替换
│  ├─ safety.py             风险门禁与停训锁
│  ├─ trend_analysis.py     7/14/30 天统计
│  ├─ state_manager.py      原子快照、写入锁、修订检查
│  └─ validation.py         JSON Schema 与非有限数校验
├─ schemas/                 user_profile / fitness_state / daily_checkin / workout_target / workout_record
├─ references/              训练、强度、调整、安全四份规则
└─ scripts/uninstall.py     卸载脚本
```

### 运行条件

Python 3.10 以上。唯一外部运行依赖是 jsonschema：

```
python -m pip install -r requirements.txt
```

每个用户使用独立的外部数据目录，个人档案不写进技能安装目录。

### 常用命令

把 `<DATA>` 换成你的个人数据目录，日期用你的当地日期：

```
python -m src.cli --data <DATA> init --input <档案JSON>
python -m src.cli --data <DATA> checkin --input <恢复反馈JSON>
python -m src.cli --data <DATA> plan --date YYYY-MM-DD
python -m src.cli --data <DATA> plan --date YYYY-MM-DD --indoors
python -m src.cli --data <DATA> record --input <训练记录JSON>
python -m src.cli --data <DATA> trends --date YYYY-MM-DD
python -m src.cli --data <DATA> status
```

自然语言由对话代理转成结构化数据再写入；不编造主观评分，缺失反馈保持未知。

### 能力边界

这是一个成人一般运动的保守规则系统。健康史字段只产生提醒，不会因为它非空就暂停建档或普通计划，也不要求先就医。当前疼痛和具体运动限制单独处理；危险症状触发持续停训锁，不提供自动解锁。

BMI、能力分数、confidence、时长乘 RPE 的负荷都属于描述性或工程指标，不是医学诊断。体重预测是有限条件下的线性外推，不是期限承诺。本技能不含饮食/热量处方、心率模型、疾病专项或术后康复方案。

### 卸载

```
python scripts/uninstall.py            # 预览
python scripts/uninstall.py --yes      # 执行
```

只删除身份匹配的 fitness-skill 目录，保留外部个人数据和其他技能。

### 免责声明

本项目是运动工程启发式，不构成医疗建议。如有疾病、伤病、术后、孕期或疼痛，请咨询合格的专业人员。使用风险自负。

### 许可

作者待定（欢迎在 issue 里说明你的偏好）。

---

## English

### What it is

fitness-skill is a pure-Python local engine driven by a conversational agent. It keeps a long-term personal fitness archive, produces abstract daily training targets (duration, intensity, load, phase), arranges concrete movements inside your time budget, and applies deterministic adjustments based on the completion ratio, RPE, fatigue, sleep and soreness you report back.

It does not train for you and it does not make medical judgments. It is an engineering system that keeps the loop of record → assess → prescribe → feedback → adapt running reliably.

### Key features

1. Staged intake. Collects information in five stages — safety, goals, baseline, preferences, capacity — at most three questions per round. Optional measurements may stay unknown; no interrogation, no maximal tests.
2. Daily loop. Reads state and the previous plan, emits abstract targets and a movement prescription. After training you record completion ratio, actual minutes, overall RPE and recovery feedback. The next plan is derived from the previous state and the rules, and it reports the reason and before/after values for every change.
3. Deterministic adaptation. Progression adds up to 5% duration every 7 days when conditions are met (2% at low data confidence); high fatigue triggers a one-off 25% deload; phases cover INIT, ADAPTATION, PROGRESS, PLATEAU and DELOAD.
4. Independent safety gate. Risk status is separated from training phase. Red-flag symptoms trigger a persistent stop-training latch, and any non-OK status emits an empty prescription — no substitute workout bypasses the gate.
5. Atomic state. One snapshot.json per data directory, with a write lock and revision counter to prevent concurrent overwrite. Corruption or conflict is never auto-reset.

### Repository layout

```
fitness-skill/
├─ SKILL.md                 Skill instructions (for the conversational agent)
├─ README.md                This file
├─ README.zh-CN.md          Detailed usage guide (Chinese)
├─ requirements.txt         Runtime dependency (jsonschema only)
├─ src/                     Engine code
│  ├─ cli.py                Command-line entry point
│  ├─ engine.py             Orchestrates modules, keeps state consistent
│  ├─ intake.py             Staged field prompts and profile merge
│  ├─ assessment.py         Descriptive assessment and data confidence
│  ├─ goal_engine.py        Goal sanity checks and conditional projections
│  ├─ adaptation.py         Phase, progression, deload, recovery rules
│  ├─ prescription.py       Movement scheduling and substitution
│  ├─ safety.py             Risk gate and stop-training latch
│  ├─ trend_analysis.py     7/14/30-day statistics
│  ├─ state_manager.py      Atomic snapshots, write lock, revision checks
│  └─ validation.py         JSON Schema and non-finite number checks
├─ schemas/                 user_profile / fitness_state / daily_checkin / workout_target / workout_record
├─ references/              Training, intensity, adaptation and safety rules
└─ scripts/uninstall.py     Uninstall script
```

### Requirements

Python 3.10+. The only external runtime dependency is jsonschema:

```
python -m pip install -r requirements.txt
```

Each user uses a separate external data directory; personal archives are never written into the skill install directory.

### Common commands

Replace `<DATA>` with your personal data directory and use your local date:

```
python -m src.cli --data <DATA> init --input <profile.json>
python -m src.cli --data <DATA> checkin --input <checkin.json>
python -m src.cli --data <DATA> plan --date YYYY-MM-DD
python -m src.cli --data <DATA> plan --date YYYY-MM-DD --indoors
python -m src.cli --data <DATA> record --input <record.json>
python -m src.cli --data <DATA> trends --date YYYY-MM-DD
python -m src.cli --data <DATA> status
```

Natural language is converted to structured data by the agent; subjective scores are never fabricated, and missing feedback stays unknown.

### Limitations

This is a conservative rule system for general adult exercise. Health-history fields produce a reminder only: they do not pause intake or block an ordinary plan, and no doctor visit is required. Current pain and specific movement restrictions are handled separately; red-flag symptoms trigger a persistent stop-training latch with no automatic unlock.

BMI, capacity scores, confidence and duration × RPE load are descriptive or engineering metrics, not medical diagnoses. Weight projections are linear extrapolations under limited conditions, not deadline guarantees. This skill contains no diet or calorie prescription, no heart-rate model, and no disease-specific or post-surgery rehabilitation protocol.

### Uninstall

```
python scripts/uninstall.py            # preview
python scripts/uninstall.py --yes      # execute
```

Removes only the identity-matched fitness-skill directory and preserves external personal data and other skills.

### Disclaimer

This project is a fitness engineering heuristic and does not constitute medical advice. If you have a disease, injury, recent surgery, pregnancy or pain, consult a qualified professional. Use at your own risk.

### License

To be decided by the author (open an issue with your preference).
