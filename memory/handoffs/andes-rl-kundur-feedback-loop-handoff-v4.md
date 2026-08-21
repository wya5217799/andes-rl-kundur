# Handoff — andes-rl-kundur 反馈环（yang-md-decoupling-marl 线，v4）

> 由 2026-08-18 凌晨会话写就（R424 收尾完成）。新会话接手用。
> 本文件只持状态与下一步；事实以仓库 artifact 为准（不重复）。
> v1/v2 已过时；v3（temp 同名目录）描述 R424 在飞状态，已由本文件取代。

## 一句话现状

R424（护栏对齐动作约束轮，CLM-1285）已完整收尾、账本全绿。核心发现 =
**实现层符号缺陷**：密封 learner 把约束项写在 actor 损失负号内
（-mean(Q + λQ_c + μ_RMS·RMS + μ_TV·TV)），梯度下降在最大化动作能量/
变化量（梯度探针内积 −97.6），对偶自强化到 10.0 上限（240 值全顶满、
RMS 残差 38.3–90.8x），演员锁死满格动作（36 块饱和占比中位 0.90、
饱和预算守卫 0→24）→ 约束机制**从未按设计被测**，本轮判负是 R423
约束层级诊断的实现层体现，不是机制结论。副作用：家族最佳无伤害剖面
（12/14/24）、公共乘子归零（6/6）；消息增量 0.0000 且两臂逐位相同 =
**限幅掩盖**，不下通信价值结论（12 对评估文件哈希互异，非读错）。
**下一单因素 = 符号改正后的约束重测（新轮、重封 learner，短预算 +
密集探针）**；P1 目标归一化仍为注册的估价修复选项。owner 三条指令
已入库（小步快跑/并发授权/研究目的）。

## 权威入口（新会话第一步）

```
cd E:\Projects\andes-rl-kundur
python memory/tools/session_context.py --json --line yang-md-decoupling-marl
```

预期 mode=manuscript 或 research（R424 已关）。必读：
- `skills/kundur-round/SKILL.md`（过程真源）
- `paper/yang_md_decoupling_marl/working/gate_calibration_log.md`
  （本线全部决策，含 R424 四行 + owner 三条 loop 级指令）
- `paper/yang_md_decoupling_marl/reports/R424.md`（本轮 feed）

## 下一轮（R425 候选）：符号改正后的约束重测

- 依据：R424 发现密封 learner 符号缺陷（约束项在负号内 = 奖励动作压力），
  机制从未按设计被测；修一行符号、新 round 重封 learner、同束重测。
- 注册的 P1 目标归一化仍是估价修复选项（critic 发散持续 Q4/Q1 ≥ 3）。
- owner 新原则：短预算（Tier-1 筛查 ~20% 步数、1-2 种子、development-only、
  全诊断探针）→ Tier-2 完整封存证据轮；预算缩短是声明协议因子，字节锚
  可比性要在 plan 显式处理。
- **新排练门**（R424 教训）：单因素加目标项的轮，rehearsal 必须跑方向检查
  （梯度探针/有限差分）钉死惩罚 vs 奖励语义,seal 前过。已写入校准日志。
- B2 五种子 runner 设计 + C1-SAC prep 文档已备好（tmp/yang_md_decoupling_marl/，
  C1 仍 owner 门槛）。

## 并行与规则（owner 2026-08-17 晚授权，勿倒退）

- 硬件有富余即并行：同线并发 round 是默认姿态（并发负载阶梯 + 总内存
  记账 + other_reserved_processes 声明），已写入 CLAUDE.md 并行预算条目 +
  SKILL.md + resume-contract。
- 研究目的 = RL 调参优化、用调好的 RL 与传统算法竞争；调参 = 单因素
  预注册轮，禁盲扫（R86 平台期规则仍活，但证据是旧束，R419+ 束单因素
  调参开放）。
- 每轮校准日志一行；每轮跑 `python tmp/yang_md_decoupling_marl/loop_round_audit.py`。

## 收尾教训（本轮新增）

- **pytest 要在 Windows 侧跑**：`$env:PYTHONPATH='E:\Projects\andes-rl-kundur\src'; python -m pytest tests -q`。
  在 WSL 里跑会让 Windows-integration 测试失败（路径 helper 期望盘符）且
  部分 ANDES 测试在仓库根留下 `kundur_full_out.*`（repo_health 报
  ROOT_UNDECLARED，需删除）。
- **旧会话遗留自动任务链**：上一会话的监控循环会在训练完成时自动启动
  evaluate/classify；接手时先 ps 查再动，避免重复启动。
- **close-out 单写者（R422 教训复发一次）**：旧会话领走 CLM-1280 空桩，
  本会话用 CLM-1285 收尾、删除空桩（CLM-1260 先例）。收尾前必须查
  现有 feed/claim。
- 给 PI 的话禁词表：`memory/tools/validate.py` `PI_PROJECT_JARGON_TERMS`
  （本轮新增教训："归一化""执行器""残差"等词禁用，写前先查）。

## 时间边界

2026-08-28 注册、2026-09-07 终稿冻结（LINE.md venue 段）。手稿 §5.2 已补
R424 段落、§6.1/§6.4/§7 已按 R424 结果修订（CLM-1285 绑定）。R425 若按
短预算原则设计，仍有足够轮次空间在冻结前走完。

## 敏感信息

无。无 API 密钥/口令；所有凭据类配置均在用户本机既有环境中。
