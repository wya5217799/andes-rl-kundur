---
round: R385
state: completed
manuscript_line: converter-vsg-pq-decoupling
opened: '2026-08-14'
closed: '2026-08-14'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R385 plan — structurally clean four-REGCV1 initialization gate

**Opened**: 2026-08-14
**Driver**: R384 showed that status-zero legacy generator chains can retain internal DAE equations; test one separately authorized construction in which those records are absent by structure while every static Kundur datum and the REGCV1 card remain fixed.
**Parent**: Q-0105; CLM-1065; R384; ADR-0017

## TL;DR

工作量：`evidence`。从 ANDES packaged Kundur static tables 生成无动态源模型的确定性 JSON，只加入同参数卡四台 `REGCV1`；一条零输入、零控制、零训练正式记录判 source equality、旧方程缺席、初始化、post-init reference、有限性和 0.2 s 漂移。PASS 只开放另轮 signed authority；STOP 结束 `REGCV1`；INVALID 不得本轮重试。

## Snapshot at plan-time (oracle as of 2026-08-14)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0104 closed-negative @ R384, by CLM-1065 — Can four ANDES REGCV1 converter-level VSG devices replace the four dynamic generator chains on the unchanged Kundur network, preserve exact one-to-one static-generator ownership and mutable Pref/Qref interfaces, and complete zero-input initialization and short TDS without numerical drift or non-finite electrical variables?
- Q-0103 closed-negative @ R369, by CLM-0990 — Does one globally fixed local-neighbour per-VSG M/D controller clear the deterministic efficacy and no-harm gate on the balanced development bank, while a bounded non-learning outcome oracle shows at least five percent additional headroom with nonconstant direct actions?
- Q-0102 closed-positive @ R366, by CLM-0980 — Can the fixed-title line freeze a 60-Hz, permission-matched per-VSG inertia/damping comparison contract and a deterministic baseline family that leaves a falsifiable learning gate without importing the old action-object mismatch or claiming storage feasibility?

## Methodology

### Research Supervisor design gate

- **唯一问题**：保持 ANDES 2.0.0、Kundur static tables、四个 static-generator 位置及 R384 `REGCV1` 参数卡不变，只把 `GENROU/TGOV1/EXDC2/Toggler` 从输入结构中完全移除后，四台 `REGCV1` 能否通过 native TDS initialization 并完成 0.2 s zero-input run？
- **materially different formulation**：R384 input 含 12 条 `u=0` legacy dynamic records；R385 derived case 只允许 `Bus/PQ/PV/Slack/Line/Area`，要求 `GENROU.n=TGOV1.n=EXDC2.n=Toggler.n=0`。这是 ADR-0017 单独注册的 structural-absence successor，不覆盖或重试 R384。
- **static-source identity**：同时绑定 packaged `kundur_full.xlsx` 与 `kundur_full.json`；逐 sheet/row/field 比较六个 static model tables（忽略 Excel-only `uid`，保留 `None`，Python numeric equality），再从 JSON 精确投影为 canonical static-only payload。任一差异在 formal attempt 前 BLOCK。
- **设备与参数**：bus/static-gen `(1,1)..(4,4)` 各加 `REGCV1`；`Sn` 继承 static gen；`fn=60`、`Tc=0.01`、`kw=0`、`kv=0.01`、`M=10`、`D=0`、`ra=0`、`xs=0.2`、`gammap=gammaq=1`；ANDES default double-loop gains。除 construction 外不改变 R384 card。
- **reference evidence**：不再在 `TDS.init()` 前用 next-float 证明 operating reference。结果记录 PFlow 后 static-gen `p/q`、TDS.init 后每台 `Pref/Qref`，按 `gammap/gammaq` 比较，absolute tolerance `1e-12`；direct software identity 与 signed dynamic authority 均留给后继 gate。
- **动态执行**：无 event、disturbance、controller、reward 或 training；native trapezoid，`tf=0.2 s`，记录 native tolerance 和 solver flags。
- **诊断**：无论 init PASS/STOP，序列化所有 `abs(fg)>=tol`/NaN 的 variable name、residual、equation string、model/idx（可解时）及 clamped-limit rows；不得再把 console-only residual 当根因证据。
- **判定量**：static-table identity/hash；allowed/forbidden model inventory；four-device mapping；post-init reference equality；setup/PFlow/TDS init/run/test；完整 DAE/REGCV1 finite guard；`Pe/Qe/dw/omega/v` zero-input drift。
- **漂移门**：每个 signal 最大绝对漂移不超过记录的 `TDS.config.tol`；不识别 asymptotic stability 或 robustness。
- **识别边界**：只识别 structurally clean four-REGCV1 equilibrium validity；不识别 signed authority、P/Q cross-response、decoupling、controller value、headroom、learning、topology generalization 或 deployment。

### Design vulnerability ledger

1. **BLOCK — hidden network change**：source format change可能解释结果；用 XLSX-vs-JSON full static-table equality、canonical derived bytes hash 和 frozen inventory修复。
2. **BLOCK — status-zero relabelled as removal**：`u=0` 不能通过；formal contract 要求 forbidden model counts 为零，并检查 DAE names/equation diagnostics 无 legacy prefix。
3. **BLOCK — zero reference false positive**：pre-init `ConstService` 不可作为 authority；只比较 post-init services 与 frozen static `p/q`，不在本轮做 perturbation。
4. **BLOCK — opaque init failure**：formal JSON 必须保存 equation-level residual table；缺失即 `ANALYSIS-INVALID`，不能产生 causal claim。
5. **QUALIFY — remaining REGCV1/slack/gain risk**：若 clean formulation 仍由 REGCV1 or network equations失败，STOP；不 post-hoc 调 gain、不换 model。

### Ask Matt TDD handoff

- 公开 seams：`build_regcv1_static_kundur_object()` 返回 system、source/derived hashes、static snapshot 和 bindings；`classify_regcv1_clean_init_record()` 从 immutable record 返回 typed decision；R385 runner 只暴露 `rehearse/prepare/execute`。
- vertical slice 1：static projection 对 exact packaged tables 保真且拒绝 drift；slice 2：constructed object 的 forbidden model counts 为零且四台 mapping 正确；slice 3：classifier 区分 PASS/STOP/INVALID 并 fail-close；slice 4：runner create-only/provenance/residual serialization。
- unit tests 可用 fake boundary；WSL package setup-only integration 属 development canary，不运行 PFlow/TDS、不进入 claim。正式 trajectory 只由 sealed execution 产生。

### Decision tree

- `REGCV1-CLEAN-INIT-PASS`：source equality、structural absence、mapping、post-init references、native solver、finite 和 drift guards 全真。
- `STOP-REGCV1-CLEAN-INITIALIZATION`：formal input/provenance 完整，但 initialization/reference/finite/drift 任一科学门失败；关闭 Q-0105 negative，停止 `REGCV1`。
- `ANALYSIS-INVALID`：source equality、seal/hash/output/attempt/record/residual diagnostics integrity 失败；保留失败，只能后继轮修工程完整性。

## Formal launch contract

- `formal_entry`: `scripts/run_r385_regcv1_clean_init_gate.py`；正式命令仅经 WSL `/home/wya/andes_venv/bin/python scripts/andes_scratch.py`。
- `rehearsal_command`: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r385_regcv1_clean_init_gate.py rehearse`。
- `rehearsal_scope`: `same-pre-attempt-path`；检查 plan/question/line/ADR、source/parent hash、installed ANDES/XLSX/JSON/REGCV1 source、static-table identity、derived-case hash、setup-only development canary、output absence、竞争进程、内存和磁盘；`physical_trajectory_executed=false`。
- `rehearsal_checks`: `source_hash`, `parent_hash`, `installed_package`, `installed_cases`, `static_table_identity`, `derived_case_determinism`, `structural_absence`, `setup_only_canary`, `output_absence`, `question_in_flight`, `active_plan`, `no_competing_research_process`。
- `wsl_python_processes`: 1；`native_threads_per_process`: 1；`host_process_budget`: 1；`other_reserved_processes`: 0。单一 quick job 不做 capacity ladder。
- `capacity_evidence`: `memory/rounds/R385/capacity_evidence.json`；记录当前 host/WSL memory、disk、竞争进程和 one-job stage cap，不执行 PFlow/TDS。
- `seal`: `/home/wya/andes_venv/bin/python scripts/run_r385_regcv1_clean_init_gate.py prepare`，绑定 rehearsal、capacity、源码、plan、question、line、ADR、route contract、installed runtime/cases 和 derived hash。
- `formal execution`: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r385_regcv1_clean_init_gate.py execute --expected-seal-sha256 <sha256>`。
- create-only result root：`results/research_loop/r385_regcv1_clean_init_gate/`；formal attempt 创建后不改 source/card/threshold，不重试、不补跑。

## Gate

PASS 需要唯一 formal record 同时通过 static source equality、legacy model/equation absence、四设备 mapping、post-init reference equality、native setup/PFlow/TDS、全有限性和 native tolerance 内 zero-input drift。PASS 只开放另轮 signed `Pref/Qref` authority；STOP 结束 `REGCV1`；INVALID 不产生科学结论。所有分支 `training_authorized=false`。

## 资产保护契约

- 不变：R384 及更早 seal/results/feed/claim/verdict；packaged ANDES cases；Kundur static tables/connectivity；R384 `REGCV1` card；旧 env/train/ranker/checkpoints；其他 manuscript lines。
- 可新增：ADR-0017、Q-0105/R385；新 static-case builder、clean-init classifier、stable runner 和定向 tests；rehearsal/capacity/seal；一个 create-only result root；正常 feed/claim/verdict/manifest/navigation。
- 禁止：修改 packaged case、把 `u=0` 称 removal、改 topology/static values、换 `REGCV2/REGF2`、改 gain/card、结果后调门、retry、controller、training、跨线写入或把 setup/test 通过写成 physical authority。

## Cross-references

- CLM-1065 / R384：status-disabled-chain formulation 在 native initialization 停止；formal JSON 未存 equation residual。
- ADR-0017：同线只授权 structural-absence REGCV1 successor；不是 R384 retry，也不授权其他 model。
- CLM-1060 / ADR-0016：ANDES/Kundur、四设备对象、physics-first gate order 和 evidence non-transfer。
