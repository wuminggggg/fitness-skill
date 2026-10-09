# fitness-skill 使用说明

维护个人运动档案，基于持续状态生成每日指标、动作处方并按反馈调整。运行包包含技能指令、业务代码、Schema、规则参考和卸载脚本。

安装完成后，执行安装的Agent应直接在当前对话开始分阶段建档：先确认年龄与运动风险，每轮最多三个问题；已有档案则继续补充，不重复创建。用户要求仅安装或暂不收集时遵循其选择。这是Agent的操作指令，不是自动启动程序。

## 运行条件

Python 3.10+，在技能目录运行 `python -m pip install -r requirements.txt`。唯一外部运行依赖为jsonschema。每个用户使用独立的外部数据目录，不在技能安装目录内存放个人档案。

## 命令

输入文件由对话代理根据用户回答创建，并遵循schemas中的格式。将以下命令中的路径替换为实际路径，日期使用用户当地日期。

```powershell
python -m src.cli --data <个人数据目录> init --input <档案JSON文件>
python -m src.cli --data <个人数据目录> checkin --input <恢复反馈JSON文件>
python -m src.cli --data <个人数据目录> plan --date YYYY-MM-DD
python -m src.cli --data <个人数据目录> plan --date YYYY-MM-DD --indoors
python -m src.cli --data <个人数据目录> record --input <训练记录JSON文件>
python -m src.cli --data <个人数据目录> trends --date YYYY-MM-DD
python -m src.cli --data <个人数据目录> status
```

`init`支持局部更新。首次先确认年龄和风险，再收集目标、可用时间、频率，之后补充测量和偏好；每次最多三项问题。可选测量允许未知。自然语言由代理转成结构化数据；不编造主观评分。

`checkin`按日期合并恢复信息；`record`绑定当天plan_id，一天一条聚合记录，相同提交不重复写入，冲突明确报错。缺失反馈保持未知。计划按日期前进，暂不支持历史修正回放。

## 模块

- intake：分阶段字段提示与档案合并。
- assessment：描述性评估、内部评分与数据充足度。
- goal_engine：目标合理性检查与条件性趋势预测。
- adaptation：训练阶段、进阶、减量与恢复规则。
- prescription：时间预算内的动作安排与同类替换。
- safety：独立风险门禁及停训锁。
- trend_analysis：7/14/30天统计和反馈覆盖。
- state_manager：原子JSON快照、写入锁与修订检查。
- engine：协调以上模块，保持跨日和同日状态一致。
- validation：JSON Schema与非有限数校验。
- cli：命令行入口。

Schema覆盖user_profile、fitness_state、daily_checkin、workout_target、workout_record。具体规则见references下四份文件。

## 状态和调整

每个数据目录使用一个snapshot.json，保存profile、state、plans、checkins、records、audit、安全锁及revision。临时文件写完后原子替换；写入锁和修订号防止并发覆盖。遇损坏或冲突不自动重置。

自动进阶只增加时长，符合条件时最多每7天5%，低数据置信度为2%。高疲劳进入一次25%减量。阶段依次支持INIT、ADAPTATION、PROGRESS、PLATEAU、DELOAD；恢复后至少重新观察21天，仅用本轮数据判断平台。

记录反馈不重写当天指标；新的安全/恢复信息仍可减量或停训。天气替换会保存处方和调整原因。动作时段包含休息，热身放松包含在总时间中。

`progression --input <剂量JSON文件> --mode time|reps|sets|difficulty`仅评估单变量进阶候选，不自动写入普通计划；超过增幅上限的离散变化会保留原剂量。

## 能力边界

当前为成人一般运动的保守规则系统。健康史字段只产生提醒，不因其非空而暂停建档或一般运动计划，也不要求先就医或提交报告。当前疼痛和具体运动限制仍单独处理；危险症状触发持续停训锁，未提供自动解锁。关键词仅为后备筛查，不能完整理解自然语言或代替医学判断。

BMI、能力分数、confidence和duration×RPE负荷属于描述性或工程指标。体重预测为有限条件下的线性外推，不是期限保证。没有饮食/热量处方、心率模型、疾病专项方案或自动器械周期。

器械、偏好和经验等字段可保存，但部分尚未参与自动处方。设备接入尚未实现；目前人工输入。没有后台定时任务、自动提醒或独立图形界面。技能由代理调用时运行。

## 卸载

脚本只依赖Python标准库。默认定位CODEX_HOME下的skills/fitness-skill；未设置时使用用户目录下的.codex/skills/fitness-skill。

预览：

```powershell
python scripts/uninstall.py
```

执行卸载：

```powershell
python scripts/uninstall.py --yes
```

可加 `--skills-dir <skills父目录>` 指定安装位置。只删除身份匹配的fitness-skill目录，保留外部个人数据、其他技能及项目ZIP。技能内部存在data目录或snapshot.json时拒绝删除；链接和目录联接同样拒绝。执行前结束正在使用技能的任务。删除不移入回收站，目录不存在时返回not_installed。
