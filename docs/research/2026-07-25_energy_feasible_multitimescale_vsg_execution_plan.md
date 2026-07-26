# 能量可行多时间尺度 VSG 研究执行计划

**日期：** 2026-07-25  
**状态：** prospective framework，尚未登记新 question、round 或 claim  
**目标期刊：** IEEE Transactions on Power Systems（TPWRS）  
**上游调研：** `docs/research/2026-07-25_energy_feasible_multitimescale_vsg_landscape.md`  
**当前证据边界：** R270 `NO-MATERIAL-MARGIN`；R271 `MODEL-CORRECTION-REQUIRED`

## 0. 这份文档怎样使用

这不是一次性 todo，也不是对所有后续阶段的执行授权。它是未来 Codex/研究任务的
入口合同：

1. 每次开始时先恢复研究程序和当前状态；
2. 一次只解锁一个可证伪 gate；
3. 每个 gate 使用独立 question、round、claim 和 verdict；
4. 前一 gate 没有正式关闭，后一 gate 不得实现；
5. 负结果按预注册停止条件关闭方向，不用新算法、阈值或场景补救；
6. 所有数值结论以真实 ANDES 轨迹和可追溯物理参数为准。

截至本文创建时，`research_goal.py --json` 返回
`no-eligible-question`，且没有 active round。因此，本文本身不允许直接运行
ANDES。未来任务必须先完成 Stage 0 的问题登记和计划预检。

### 当前唯一建议的下一目标

> 在预先冻结的功率、能量、SOC、headroom、ramp、lag、效率及 converter
> capability 合同下，判断独立的经典有功控制器能否相对当前无储能执行器系统，
> 在共同频率恢复端点上产生至少 2% 的配对改善，同时不破坏同步、峰值、
> RoCoF、失败率、动作和能量守卫。

这是 **Gate 1：active-power authority**。Gate 2–7 暂不授权。

## 1. Phase

- **Primary phase：** Vibe Coding，用最小可验证实现回答物理可行性问题。
- **Secondary phase：** Vibe Writing，只用于计划、provenance、verdict 和
  PI briefing，不写投稿论文正文。
- **Dormant phase：** Vibe Figure。Gate 1 不生成论文图；必要诊断图必须由
  可复现脚本从原始结果生成。

## 2. Behavioural rules recap

以下六条为每次未来任务的启动合同：

1. AI 可协助文献整理、代码脚手架、调试、验证自动化和语言润色。
2. 研究问题、物理合同、实验设计、阈值、技术路线、核心结论与新颖性由用户
   及 PI 决定，并且必须能够脱离 AI 解释。
3. AI 生成的代码逐行审查并测试；文字逐句核对；数值追溯到原始结果。
4. 不允许 AI 生成未经用户阅读和确认的引用或物理参数来源。
5. 不伪造数据、轨迹、失败修复、实验步骤或“合理补点”。
6. 遵守 IEEE、TPWRS、学校和课题组当时有效的 AI 披露规则。

任何一条不满足，暂停当前任务，不继续实验。

## 3. 证据权威和 supersession

未来任务按以下优先级解释项目：

1. `memory/rounds/R270/verdict.md` 和 `memory/rounds/R271/verdict.md`：
   当前已测物理边界；
2. `memory/claims/CLM-0555.md`、`CLM-0560.md`、`CLM-0565.md`：
   原子化 measured/decision provenance；
3. `docs/research/2026-07-25_energy_feasible_multitimescale_vsg_landscape.md`：
   新执行器方向和文献边界；
4. 本执行计划：未来 gate 顺序和行为合同。

`docs/research/2026-07-25_idea_evaluation_research_direction.md` 中
“先做 \(M/D\)-only graph residual vertical slice”的路线已被 R270/R271
后续证据取代。该文件仍是历史决策记录，但不得再作为立即实现 graph policy 的授权。

### 不得混淆的三个结论

- R270/R271 否定的是当前模型上的 \(M/D\)-only 共同频率恢复，不是否定
  \(M/D\) 的 RoCoF、峰值和同步作用。
- `GENCLS + ESD1` 是“独立 VSG 代理 + GFL BESS 有功支持”的混合代理，
  不是统一物理 GFM-BESS。
- Gate 1 只判断 explicit active-power authority；它不能产生 topology、
  stability、converter inner-loop、EMT 或 HIL 结论。

## 4. 总体 workflow plan

| Time block | Phase | Activity | Tool | User/PI check |
|---|---|---|---|---|
| Stage 0A，0.5–1 天 | Research design | 冻结 Gate 1 objective、参数来源、阈值和非目标 | Codex + Markdown | 用户能独立解释每个设计选择 |
| Stage 0B，0.5 天 | Governance | 登记 programme question，原子预留 round/claim，运行 preflight | Codex + repo tools | selector 返回 ready goal；无 active round |
| Stage 1A，1–3 天 | Vibe Coding | 合成测试和最小 BESS/有功接口，不运行正式 bank | Codex + pytest | 功率符号、SOC、能量、限幅、reload 合同通过 |
| Stage 1B，1–2 天 | Vibe Coding | 单场景 real-ANDES smoke 和零输入审计 | WSL real ANDES | V4 anchor 不变；混合代理语义正确 |
| Stage 1C，2–5 天 | Experiment | 只在 development bank 调经典控制并冻结 primary controller | WSL real ANDES | 调参预算匹配；不看 sealed bank |
| Stage 1D，按轨迹时长 | Experiment | 生成并封存新 bank，运行正式 Gate 1 | WSL real ANDES `--resume` | bank/controller/source hash 在首条正式轨迹前冻结 |
| Stage 1E，0.5–1 天 | Analysis | 配对统计、failure/tail/energy/action 审计 | Python reusable evaluator | 不删失败行；不更换阈值或 primary controller |
| Stage 1F，0.5 天 | Vibe Writing | claim、question、verdict、validation、PI briefing | Codex + memory tools | 用户逐句确认结论与原始 JSON 一致 |
| Gate 2+ | Dormant | 仅在前一 gate 阳性且已关闭后新开任务 | 新 question/round | 本轮不得顺带执行 |

时间是工作块估计，不是截止日期。若同一问题连续三次实现失败，停止 patch loop，
回到 Stage 0 重新审查接口和物理合同。

## 5. Stage 0：执行前必须锁定的研究合同

### 5.1 Required reading

未来任务必须完整读取：

- `AGENTS.md`
- `CLAUDE.md`
- `memory/RESEARCH_PROGRAM.md`
- `memory/STATE.md`
- `memory/rounds/R270/verdict.md`
- `memory/rounds/R271/verdict.md`
- `memory/claims/CLM-0555.md`
- `memory/claims/CLM-0560.md`
- `memory/claims/CLM-0565.md`
- `docs/research/2026-07-25_energy_feasible_multitimescale_vsg_landscape.md`
- `docs/eng-notes/NOTES_ANDES.md`
- installed ANDES 2.0.0 `ESD1`、`PVD1`、`DG.set_paux()` 及拟复用控制模型源码。

### 5.2 Session bootstrap

```powershell
python memory/tools/research_goal.py --json
python memory/tools/reserve_round.py --list-active
git status --short
```

解释规则：

- 有 active round：恢复并关闭它，不开新工作；
- selector 为 `no-eligible-question`：只做问题/程序登记，不预留实验 round；
- selector 返回 ready goal：使用其 objective、required reading、scope limits、
  verification 和 stop conditions，不自行改写；
- 保存并保护当前 dirty worktree；不 stage、覆盖或清理无关文件。

### 5.3 用户/PI 必须确认的科学选择

正式 round 前必须把以下 checkbox 变为已确认，并在 round plan 中记录来源：

- [ ] 同意 Gate 1 是下一唯一问题；
- [ ] 同意 T2 只作为混合代理 feasibility，不作统一 GFM-BESS 机理证据；
- [ ] 同意复用 R270 的 **2% materiality floor** 作为 Gate 1 最低通过阈值，
      或在看到任何新轨迹前给出替代值及理由；
- [ ] 确认 BESS 额定功率和能量容量的公开、可追溯来源；
- [ ] 确认 `SOCmin/max/init`、充放电效率和正负 headroom；
- [ ] 确认 active-power ramp、lag、持续时间和恢复职责；
- [ ] 确认 P/Q/current capability 与 priority 的第一阶段简化；
- [ ] 确认 disturbance duration 与仿真 horizon 足够观察慢层恢复；
- [ ] 确认 primary classical controller 的选择规则与调参预算；
- [ ] 确认 TPWRS 仍是目标期刊，并在投稿前重新检查 AI policy。

任何物理参数不得由 AI 为“让仿真能跑”而填充。缺少来源时，Gate 1 状态为
`BLOCKED-BY-PHYSICAL-CONTRACT`，不启动正式轨迹。

### 5.4 问题和 programme 登记

由于当前没有 eligible question，未来获用户授权的任务先：

1. 创建下一唯一 question 文件，使用 `memory/questions/_TEMPLATE.md`；
2. 把本 Gate 1 objective、required reading、verification、scope limits 和
   stop conditions 加入 `memory/RESEARCH_PROGRAM.md`；
3. 运行：

```powershell
python memory/tools/validate.py
python memory/tools/render.py
python memory/tools/research_goal.py --json
```

只有 selector 返回该问题的 ready goal 后，才原子预留：

```powershell
python memory/tools/reserve_round.py --strict-no-active --write-plan-stub
python memory/tools/reserve_claim.py --round R<N> --type finding
```

`R<N>` 和 `CLM-NNNN` 必须使用工具实际返回值，不手工猜号。完成正式 plan 后、
运行任何 ANDES 前：

```powershell
python memory/tools/round_preflight.py R<N> --json
```

exit code 2 时不得启动；exit code 1 必须人工复核。

## 6. Gate 1：active-power authority 的最小实验

### 6.1 单一可证伪问题

在冻结的当前四 VSG 快层下，增加一个独立且受功率/能量约束的 BESS 慢有功层。
判断一个预先指定的经典有功控制器，能否相对无新增 BESS 的 matched baseline，
同时改善：

1. full-horizon physical VSG-mean IAE；
2. final-window common-frequency absolute deviation；

并守住同步、安全、失败、动作、SOC 和能量边界。

不训练神经网络，不动态调 \(M/D\)，不实现 graph policy。

### 6.2 Frozen model semantics

- 保留当前 V4 和 R268/R270 droop prior 的默认行为；
- 在新路径中组合 `ESD1` 与 `DG.set_paux()`；
- 新路径使用独立类/adapter/case，不在 V4 默认路径中静默加入 BESS；
- `M/D` 在 Gate 1 中冻结，不使用 R270 outcome-seeing oracle；
- 所有有功请求经过同一个 power、ramp/lag、SOC/energy 和 capability contract；
- 记录 BESS electrical output、commanded power、SOC、累计充放电能量、限幅原因；
- 不把 `P_es` measured output 当成 independent command；
- 不声称 GFM-BESS、inner-loop 或 converter fault/current-limit 机理。

### 6.3 Controller set and attribution

Development bank 可以比较：

1. `no_new_bess`：当前系统；
2. `bess_p_f_droop`；
3. `bess_droop_pi_agc`；
4. `bess_constrained_mpc`。

约束：

- 四者共享同一 BESS 物理合同；
- 为 PI/AGC 与 MPC 预注册各自调参/轨迹预算；
- primary controller 必须只由 development bank 选定；
- 在打开 sealed bank 前冻结 controller config、source hash 和选择理由；
- 正式 gate 只检验该 primary controller 对 matched baseline；
- 其他控制器作为预声明 secondary comparison，不允许 formal best-of 选择。

这样可以避免把 controller selection 的收益误归因于“两层结构”。

### 6.4 Test-first implementation order

每个步骤都遵循“requirement → test → implementation → run → inspect”：

1. **参数 schema 测试**
   - 单位、system base、正负功率方向；
   - `Pmax_ch/dis`、`E_rated`、SOC、效率、ramp/lag、capability；
   - 非法或无来源字段 fail closed。
2. **合成能量测试**
   - 放电使 SOC 按效率下降；
   - 充电使 SOC 按效率上升；
   - 能量积分和 power trace 数值闭合；
   - SOC 上下界正确阻断功率。
3. **接口测试**
   - `set_paux()` 的符号、单位、reset、deterministic reload；
   - zero command 不产生隐藏能量或控制漂移。
4. **控制器测试**
   - droop/PI/MPC 输出共享同一投影；
   - anti-windup、ramp、saturation 原因可审计；
   - controller state 在 reset 后清空。
5. **evaluation 测试**
   - common/differential endpoints；
   - final-window identity；
   - failure row、zero denominator、non-finite、paired statistics；
   - SOC/energy/capability violation 和 saturation duration。
6. **real-ANDES smoke**
   - 先 1 条、短 horizon；
   - 再 1 条完整 horizon；
   - 通过后才生成正式 sealed bank。

Gate 1 必须保持现有 `tests/test_v4_env_regression.py` 的 1e-9 contract。

### 6.5 Scenario and sealing protocol

- R265/R267/R268/R270 场景只能用于 smoke、debug 或 development；
- formal verdict 使用新的 no-anchor bank；
- 默认 feasibility 规模为 **20 个配对场景**，若物理合同要求更长 horizon，
  可在看结果前由 round plan 降低或提高，但必须说明统计与算力代价；
- scenario generator、seed、bytes、SHA-256、environment/config/source/checkpoint
  hashes 在首条 formal trajectory 前冻结；
- horizon 至少覆盖最慢 closed-loop time constant 的 5 倍，并设 final window；
- formal runner 必须支持 `--resume`，wrapper timeout 后不重跑已完成 traces；
- 所有 controller-scenario completion rows 都保留，失败不是可删除异常值。

real ANDES 只在 WSL 运行：

```powershell
wsl.exe -- /home/wya/andes_venv/bin/python <runner> --resume
```

长任务使用可 yield 的后台执行，不用 Windows ANDES。

### 6.6 Endpoints

Co-primary：

- physical VSG-mean IAE；
- final-window common-frequency absolute mean。

Secondary physical：

- terminal common-frequency sample；
- restoration/settling time；
- normalized synchronization loss；
- worst-bus peak；
- max sampled RoCoF；
- inter-area oscillation summary。

Actuator and feasibility：

- BESS commanded/actual power；
- charge/discharge energy；
- terminal/min/max SOC；
- positive/negative headroom；
- ramp/lag and saturation duration；
- P/Q/current capability activation；
- action L1 与 total variation；
- completion、TDS failure、runner error。

`geo` 不作为 random held-out bank 的主终点；`cum_rf` 只作历史同步诊断。

### 6.7 Proposed pre-registered decision gate

以下 2% 是沿用 R270 的 feasibility materiality floor。用户/PI 可在 Stage 0
替换，但一旦 formal plan 通过 preflight 就不能再改。

#### AUTHORITY-POSITIVE

所有条件同时成立：

- primary active-power controller 的 mean VSG-mean IAE 相对 matched baseline
  改善至少 2%，paired bootstrap 95% interval 上界低于 0；
- final-window common absolute mean 改善至少 2%，95% interval 上界低于 0；
- completion/TDS failure 不恶化；
- normalized synchronization loss、worst-bus peak 和 max RoCoF 均不恶化超过 5%；
- action L1/TV 不恶化超过 25%；
- SOC、energy、power、ramp 和 capability violation 为 0；
- provenance、source、bank 和 controller hashes 全部匹配。

关闭 Gate 1 为 positive。下一任务才允许登记 Gate 2。

#### AUTHORITY-PARTIAL

物理合同和 provenance 有效，但仅一个 co-primary endpoint 通过，或共同恢复改善
被同步/安全/动作/能量守卫抵消。

关闭 Gate 1 为 partial。不得进入 learning 或 topology；下一 question 只能诊断
预注册失败机制，而且不得更换 bank、阈值或多个参数。

#### NO-MATERIAL-AUTHORITY

有效 formal 结果没有任何预指定经典有功控制器满足 joint gate。

关闭 Gate 1 为 negative。停止 AI/controller expansion。优先审查：

- disturbance 是否包含真实持续失衡；
- 原同步机 governor/AGC 是否已经承担恢复；
- BESS placement/capacity 是否来自错误物理层级；
- 正序模型是否无法表达所需机制。

不得用新 RL、更多容量、另一个 seed 或更宽阈值补救。

#### INVALID

source/bank/controller drift、参数无来源、初始化失败、能量不闭合、formal row
缺失、runner error 或统计实现错误。

只修 integrity defect，按相同合同 `--resume`。不得把 invalid 解释为物理负结果。

## 7. 后续 gates：默认休眠

### Gate 2：fast \(M/D\) independent value

**Entry：** Gate 1 `AUTHORITY-POSITIVE` 且 round 已关闭。  
**Question：** 在冻结的同一慢有功 controller 下，预先指定的 fast \(M/D\) law
是否仍对 RoCoF、峰值、同步和 inter-area oscillation 提供独立收益？  
**Stop：** 若无独立收益，后续研究缩为慢层，不保留双层故事。

### Gate 3：non-additive fast/slow value

**Entry：** Gate 2 positive。  
**Question：** 快慢联合是否优于最佳单层和等计算/等动作预算的经典联合 controller？  
**Stop：** 若无非加和收益，删除双层新颖性，不因复杂度保留结构。

### Gate 4：learning-gap diagnosis

**Entry：** Gate 3 positive。  
**Question：** 调优 droop+PI/AGC 或 constrained MPC 是否在预先冻结的 SOC
饱和、连续扰动、局部观测、delay 或 topology shift 下出现可重复、物理实质缺口？  
**Stop：** 经典控制无稳定缺口时，结论为 `NO-RL-NEEDED`，不训练 residual。

### Gate 5：bounded residual pilot

**Entry：** Gate 4 明确了单一 learning gap。  
先做 fixed-topology、memoryless、training/deployment-consistent residual；
必须有 amplitude/rate/energy projection 和 classical fallback。它未通过 physical
co-primary、tail、failure、action 和 energy joint gate 前，不得做 graph policy。

### Gate 6：whole-topology generalisation

**Entry：** Gate 5 positive。  
定义 variable-\(N\) graph contract、matched non-graph baseline、entire held-out
graphs、VSG-count 和 communication topology。整图不胜 matched MLP 时关闭
topology thesis。

### Gate 7：safety and high fidelity

**Entry：** Gate 6 positive。  
再进入 stability-screened projection、delay/dropout/outage/fault stress、
第二仿真器或 HIL/RTDS。ANDES 正序结果不能单独支持 converter inner-loop 或
fault-current claim。

## 8. Planned code and artifact boundaries

具体文件名由 formal round plan 冻结，但结构必须可复用：

- 一个新环境/adapter 路径，保持 V4 默认路径不变；
- 一个 reusable energy/power contract 模块；
- 一个 reusable classical controller/evaluator 模块；
- 一个 resumable formal runner；
- focused unit/integration tests；
- source-hashed `results/r<N>_*`；
- question、claim、round plan/verdict；
- 无 manuscript、paper figure 或新 neural checkpoint。

避免 `_rNN_oneoff.py`。相同模式出现第二次前就抽成
`src/andes_rl_kundur/` 或 `memory/tools/` 中的可维护接口。

## 9. Verification and closure contract

实现期间每个小步骤先运行 focused tests。正式启动前至少运行：

```powershell
python memory/tools/round_preflight.py R<N> --json
python -m pytest tests -q
python memory/tools/dual_metric_lint.py
```

完成 formal batch 后：

```powershell
python memory/tools/validate.py
python memory/tools/render.py
python memory/tools/research_goal.py --json
```

round 必须包含：

- positive、partial、negative 或 invalid 的明确 verdict；
- measured provenance 和 source/bank/controller hashes；
- question closed/advanced/opened 三节；
- claim back-reference；
- `## 给 PI 的话`。

关闭任务时必须把 `## 给 PI 的话` 正文逐字粘贴到聊天，不能只给文件链接。

## 10. Tool recommendations

| Phase | Primary tool | Alternative | Reason |
|---|---|---|---|
| Research orchestration | Codex desktop/CLI | Claude Code | 可读取 repo memory、运行 Windows/WSL、维护长任务和验证 |
| Coding | Codex + pytest | Cursor Plan/Agent Mode | 本项目需要先计划、再做小步 test-first 修改 |
| real simulation | WSL `/home/wya/andes_venv/bin/python` | none | ANDES 物理结果的平台记录 |
| statistics | Python reusable evaluator | R only if predeclared | 现有 paired bootstrap、failure interval、CVaR 可复用 |
| diagnostic plots | Matplotlib/Seaborn | PGFPlots later | 可重复生成，不手工修改数据点 |
| research records | Markdown + repo memory tools | none | 与 claim/question/round/STATE 合同一致 |
| manuscript polish | 用户草稿 + AI polish | LanguageTool | 只在有 measured claim 后启用，逐句复核 |

网络或模型服务不稳定时，不让云端 agent 持有无法恢复的长仿真；formal runner
和 provenance 必须在本地/WSL 可独立恢复。

## 11. Red-line reminders

- 不把本文或 AI 生成段落原样复制进论文；
- 不让 AI 填充物理参数、BibTeX、实验结果或缺失数据；
- 不从 sealed bank 反向选择 controller、阈值、容量或 horizon；
- 不把失败 controller 行删除为“异常值”；
- 不把 `GENCLS+ESD1` 写成统一物理 GFM-BESS；
- 不把同步改善写成共同频率恢复；
- 不用 `geo` 代替 physical endpoints；
- 不在 Gate 1 顺带实现 residual、GNN、stability proof、HIL 或论文图；
- 不修改或清理用户已有 dirty-worktree 内容；
- 不提交 AI-assisted paper prose 前跳过 IEEE/TPWRS AI policy 检查。

## 12. Integrity gate plan

每个 future task 关闭前由用户确认：

- [ ] 所有引用已在出版社、DOI、DBLP 或 arXiv 核验，用户至少阅读摘要；
- [ ] 每个物理参数有可追溯来源和单位换算；
- [ ] 每个代码改动已阅读并通过 focused/full tests；
- [ ] 每个 numerical claim 可定位到正式 JSON/trace；
- [ ] 阈值、bank、primary controller 和 source 在 formal 结果前冻结；
- [ ] negative/partial 结果没有被重命名为“接近成功”；
- [ ] verdict 由证据决定，而不是由 AI 的语言强度决定；
- [ ] 用户能独立解释模型、控制器、实验设计和结论；
- [ ] 当前 IEEE/TPWRS 与学校 AI-disclosure policy 已重新检查。

截至 2026-07-25，IEEE Author Center 的公开政策要求：论文中使用 AI 生成的
文本、图、图像或代码时，应在 Acknowledgment 说明 AI 系统、涉及部分及使用程度；
仅用于编辑和语法增强通常不在强制披露意图内，但 IEEE 仍建议披露。政策会变化，
投稿前以官方页面为准：

<https://journals.ieeeauthorcenter.ieee.org/become-an-ieee-journal-author/publishing-ethics/guidelines-and-policies/submission-and-peer-review-policies/>

## 13. 给下一任务的可复制启动提示

```text
继续 TPWRS 自动研究程序，但只执行
docs/research/2026-07-25_energy_feasible_multitimescale_vsg_execution_plan.md
中当前解锁的 gate。

先完整读取 AGENTS.md、CLAUDE.md、memory/RESEARCH_PROGRAM.md、
memory/STATE.md、R270/R271 verdict、CLM-0555/0560/0565、上游 landscape
和 execution plan。运行 research_goal.py --json、reserve_round.py
--list-active 与 git status。

若有 active round，恢复并关闭；若 selector 仍为 no-eligible-question，
只完成 Stage 0 的 question/programme 登记、validate、render，不运行 ANDES。
若 selector 返回 Gate 1 ready goal，使用其原文目标和限制，原子预留 round/claim，
先写 formal plan、运行 preflight，再按 test-first、小步、real-ANDES-in-WSL、
sealed-bank、--resume 和 prospective stop rules 执行。

本任务不得执行 Gate 2 以后内容，不得训练网络，不得实现 GNN，不得写论文正文。
结束时完成 verdict、claim/question 更新、validate、render，并逐字交付
“## 给 PI 的话”。
```
