# R440 execution amendment — 汇总函数名修复 (2026-08-20)

**Precedent**: R281/R283/R436 execution_amendment files (执行层声明, 不改
plant / 数据口径 / 判定树). 本修正案声明: R440 正式 shard 第一波 9/10
因 runner 汇总调用名错误崩溃; 修复只动汇总调用, plant/数据口径/判定树
全未动; 已落盘的 n2_out_Line_7_Line_8 输出有效 (功率流不收敛为真实
科学结果, 记录不判, 与 plan 一致)。

## 触发

seal 后第一波 shard (driver log
`tmp/andes/R440_shard_logs_20260819T172626.243036Z/`, 8 workers): 9 个
shard exit 1, 全部 `AttributeError: module '_r440_r413_parent' has no
attribute 'summarize_arm_records'`。R413 链 (gate_b3_deterministic) 的
真名是 `summarize_phase_records(records, *, phase, selected_arm_id=None,
contract=None)`, 返回 `{"phase", "record_count", "arm_summaries"}`。
rehearsal 只走轨迹路径 (EIG gate + bandpass + delay 轨迹), 未覆盖汇总
调用 — 与 R439 的 oracle 路径同一教训。

## 修复 (`scripts/run_r440_robustness_expansion.py`)

- `_summarize_block`: 改调 `r413.summarize_phase_records(list(records),
  phase="development", contract=contract)`, 返回 `phase["arm_summaries"]`。
  (分层修复: ① 函数名 `summarize_arm_records` ->
  `summarize_phase_records`; ② phase 用 "development" — 冻结的
  development 银行 arm_ids/probe 条件与 R440 block 完全一致, 而
  evaluation 银行要求注册 selected candidate, 语义不匹配; ③
  summarize_phase_records 校验整相银行 (3 臂 × 10 job = 30 记录),
  所以 `_run_scenario_shard` 改为一次收集三臂全部记录、单次 summarize
  后按 arm_id 索引, 与 R413 `_variant_summary` 的用法一致。)
- seal 的 sources.runner sha 因本修正过期; 本修正案覆盖重跑执行
  (runner 修复后 sha 记录于重跑 driver_result)。

## 执行

- n2_out_Line_7_Line_8 (8-9 走廊双回全断): 功率流 27 次迭代不收敛,
  按 plan 记录不判, 输出已落盘保留 (exit 0, 不重跑)。
- 其余 9 shard (7 N-2 + 2 delay) 修复后重跑 (driver `--only`)。

## 边界

- 不改 plant, 不改数据口径 (zero/local/bandpass_k3p5 三臂同条件,
  R409 阈值, R379 守卫), 不改判定树 (ROBUSTNESS-EXPANDED /
  BOUNDED-FAILURE / CANARY-INVALID)。
- 本修正案只替换有缺陷的汇总调用路径。
