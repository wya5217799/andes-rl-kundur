---
round: R384
state: completed
manuscript_line: converter-vsg-pq-decoupling
opened: '2026-08-14'
closed: '2026-08-14'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R384 plan — four-REGCV1 object and zero-input initialization gate

**Opened**: 2026-08-14
**Driver**: 在任何 P/Q 控制或学习比较前，先验证四台 converter-level VSG 能否在不改 Kundur 网络连接的条件下共同替换原动态机组、正确绑定两种设定值接口并保持零输入平衡点。
**Parent**: Q-0104；CLM-1060；R383；ADR-0016

## TL;DR

工作量：`evidence`。一条零输入、零控制、零训练的 ANDES 正式记录；只判四台 `REGCV1` 的对象映射、接口身份、初始化、有限性和原生容差内漂移。PASS 只开放另轮带符号动态 `Pref/Qref` 控制权门；有效失败停止本 formulation。

## Snapshot at plan-time (oracle as of 2026-08-14)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0103 closed-negative @ R369, by CLM-0990 — Does one globally fixed local-neighbour per-VSG M/D controller clear the deterministic efficacy and no-harm gate on the balanced development bank, while a bounded non-learning outcome oracle shows at least five percent additional headroom with nonconstant direct actions?
- Q-0102 closed-positive @ R366, by CLM-0980 — Can the fixed-title line freeze a 60-Hz, permission-matched per-VSG inertia/damping comparison contract and a deterministic baseline family that leaves a falsifiable learning gate without importing the old action-object mismatch or claiming storage feasibility?
- Q-0101 closed-positive @ R365, by CLM-0975 — Does the existing ANDES V4 candidate provide four separately addressable VSG agents with independent bounded inertia and damping actions, causal local-neighbour observations, measurable differential dynamics, and nonzero network-transmitted action authority?

## Methodology

### Research Supervisor design gate

- **唯一问题**：四台 `REGCV1` 能否在原 Kundur 网络上替换四条动态机组链，保持一对一静态机组归属、可独立读写并恢复的 `Pref/Qref` 接口，并完成零输入短时仿真？
- **对象**：ANDES 2.0.0 packaged `kundur/kundur_full.xlsx`；保留 bus、branch、load、Slack/PV 和 connectivity；禁用四台 `GENROU` 及其相连 governor/exciter；在 bus/static-gen `(1,1)..(4,4)` 各加一台 `REGCV1`。
- **参数卡**：每台 `Sn` 继承静态机组；`fn=60`、`Tc=0.01`、`kw=0`、`kv=0.01`、`M=10`、`D=0`、`ra=0`、`xs=0.2`、`gammap=gammaq=1`；双环增益保持 ANDES 2.0.0 默认值。参数不在本轮结果后改变。
- **接口身份**：setup 后经 `RenGen.get/set_pref` 与 `get/set_qref` 对每台写入该值朝正无穷方向的下一个可表示浮点数，立即读回并恢复；非目标设备不得变化。该检查只证明软件接口映射，不证明动态功率 authority。
- **动态执行**：无 Toggler 事件、无扰动、无 controller；原生 fixed-step trapezoid，`tf=0.2 s`，其余 solver 配置记录进结果。
- **判定量**：设备/母线/静态机组 inventory；被替代同步链 active count；setup/PFlow/TDS init/run/test 状态；完整 DAE 与 `REGCV1` state/algebraic finite guard；初始化到终点的 `Pe/Qe/dw/omega/v` 最大绝对漂移。
- **漂移门**：最大漂移不得超过本次运行记录的 ANDES `TDS.config.tol`；不用旧线性能阈值，不推断稳定裕度。
- **识别边界**：一条 equilibrium job 只识别对象存在、接口身份和短时数值平衡；不识别带符号动态 authority、P/Q cross-response、controller efficacy、decoupling、headroom、MARL 或泛化。

### Ask Matt TDD handoff

- 预先确认的公开 seams：`build_regcv1_kundur_object()` 返回可检查的四设备系统/绑定；`classify_regcv1_object_record()` 从完整记录返回 typed decision；R384 runner 的 `rehearse/prepare/execute` create-only lifecycle。
- 每个 vertical slice 先写公开行为测试再写最小实现；ANDES 作为 WSL 系统边界，不 mock 内部模型。纯 classifier 用 synthetic records；真实集成只在正式入口。
- 可复用 builder 进 `src/andes_rl_kundur/env/andes/`，判定器进 `src/andes_rl_kundur/evaluation/`，脚本只做稳定执行 adapter。

### Decision tree

- `REGCV1-OBJECT-INIT-PASS`：所有 identity、replacement、setpoint round-trip、native solver、finite 和 drift guards 全真。
- `STOP-REGCV1-OBJECT-INITIALIZATION`：formal input/provenance 完整，但任一科学对象门失败；关闭 Q-0104 negative，禁止在同一轮换模型、改参数或重试。
- `ANALYSIS-INVALID`：seal/source/case/output/attempt/record inventory 或 runner integrity 失败；保留失败，仅后继轮可修复。

## Formal launch contract

- `formal_entry`: `scripts/run_r384_regcv1_object_gate.py`；正式命令只经 WSL `/home/wya/andes_venv/bin/python scripts/andes_scratch.py` 执行。
- `rehearsal_command`: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r384_regcv1_object_gate.py rehearse`。
- `rehearsal_scope`: `same-pre-attempt-path`；检查 plan/question/line/ADR、source hash、installed ANDES/case、合同闭合、结果不存在、竞争进程、内存和磁盘；`physical_trajectory_executed=false`。
- `rehearsal_checks`: `source_hash`, `parent_hash`, `installed_package`, `installed_case`, `output_absence`, `question_in_flight`, `active_plan`, `no_competing_research_process`。
- `wsl_python_processes`: 1；`native_threads_per_process`: 1；`host_process_budget`: 1（本轮只有一个独立 job，属于 stage/job-count 硬上限，不声称整机容量只有一进程）；`other_reserved_processes`: 0。
- `capacity_evidence`: `memory/rounds/R384/capacity_evidence.json`；rehearsal 记录当前逻辑处理器、物理/可用内存、磁盘、竞争进程和 one-job cap，不执行物理轨迹。该 quick run 不做成本更高的 capacity ladder。
- `seal`: `/home/wya/andes_venv/bin/python scripts/run_r384_regcv1_object_gate.py prepare`，绑定 rehearsal、capacity、源码、plan、question、line、ADR、安装包和 case hash。
- `formal execution`: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r384_regcv1_object_gate.py execute --expected-seal-sha256 <sha256>`。
- 结果 create-only 到 `results/research_loop/r384_regcv1_object_gate/`；formal attempt 创建后不重试、不改参数、不改门、不补跑。

## Gate

PASS 需要唯一 formal record 同时通过四设备映射、旧动态链禁用、`Pref/Qref` 精确逐机读写恢复、原生 setup/PFlow/TDS 检查、全有限性及 native tolerance 内零输入漂移。PASS 仅开放 Q-0105 候选的带符号动态 authority 设计；STOP 结束 `REGCV1` formulation；INVALID 只允许后继轮修工程完整性。任何分支均 `training_authorized=false`。

## 资产保护契约

- 不变：旧四条论文线的 feed/claim/result/checkpoint/plan/verdict；V4/base env/train/ranker；packaged Kundur 文件；R382 及以前所有封印结果。
- 可新增：Q-0104/R384；新 line 的 builder、classifier、stable runner、定向 tests；本轮 rehearsal/capacity/seal；一个 create-only result root；正常 feed/claim/verdict/manifest/navigation。
- 禁止：改 Kundur connectivity、覆盖 package case、修改旧 env、换 `REGCV2/REGF2`、结果后调参数或阈值、重试、controller、training、另一 line 写入或把导入成功写成物理有效。

## Cross-references

- CLM-1060 / R383：新 line、平台/拓扑、证据隔离和 gate order。
- ADR-0016：`REGCV1` 是首个 formulation，失败后不得同轮替换模型。
- ANDES 2.0.0 local source：`REGCV1` replaces one `StaticGen` and declares `pref/qref/vref` setpoints；只作设计输入，R384 formal record 才是本 line evidence。
