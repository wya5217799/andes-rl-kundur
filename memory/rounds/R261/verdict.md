# R261 verdict — three correctness risks confirmed; two fixed, frequency basis made explicit

**Date**: 2026-07-24
**Status**: CLOSED-CORRECTION
**Type**: correctness (real ANDES WSL + deterministic regression)
**Performance metrics**: N/A — no training, SOTA, geo, or cum_rf comparison

## TL;DR

R261 live-validated the three risks pre-registered after the repository audit:

1. **60/50 Hz mismatch CONFIRMED live**: ANDES 2.0.0 loads Kundur with
   `GENROU.fn=60` and `Line.fn=60`; project contract is 50 Hz.
2. **Failed-trace integrity bug CONFIRMED and FIXED**:
   `paper_path` dropped `tds_failed`, and the canonical summary would compute a
   headline from the partial trace.
3. **Recurrent Bellman-target alignment bug CONFIRMED and FIXED**:
   target state skipped the current replay transition and target-critic state
   followed a hypothetical target-action branch.

No historical result was overwritten. The recurrent correction covers nine
agent classes. V4 retains its frozen legacy 50-Hz control semantics, but every
new environment/trace record now exposes the ANDES physical 60-Hz basis and
labels which basis the legacy metrics use (ADR-0006).

## Methodology

### Environment

- WSL: Ubuntu 2
- Python: 3.12.3 (`/home/wya/andes_venv/bin/python`)
- ANDES: 2.0.0
- PyTorch: 2.10.0+cu128
- NumPy: 2.4.3
- Case:
  `/home/wya/andes_venv/lib/python3.12/site-packages/andes/cases/kundur/kundur_full.xlsx`

### Feedback loops

- Real ANDES load and WSL V4 trajectory tests for frequency calibration.
- Fake-env `tds_failed=True` scenario at the canonical `run_scenario` seam.
- Real `score_trace_files()` call on a shortened, failed baseline trace.
- Deterministic tagged recurrent networks where observations/actions encode
  their time index and hidden state is auditable by exact equality.

The failing regressions were run before production fixes. Observed pre-fix
signals:

- `record["tds_failed"]` raised `KeyError`.
- `score_trace_files()` did not reject the failed partial trace.
- target actor received `[10, 30]` instead of `[10, 20, 30]`.

## Finding 1 — live 60/50 Hz calibration mismatch

### Result

| Source | Nominal frequency |
|---|---:|
| ANDES GENROU | 60.0 Hz |
| ANDES Line | 60.0 Hz |
| Project `KUNDUR.fn` / V4 `FN` | 50.0 Hz |

CLM-0171 is therefore not a stale cached-file artifact. The legacy-to-physical
absolute-deviation scale remains `60/50 = 1.2`.

### Decision

R261 does **not** mutate V4 dynamics or reinterpret historical checkpoints.
ADR-0006 establishes dual reporting:

- legacy fields stay on the frozen 50-Hz control basis;
- physical fields use the detected ANDES nominal frequency;
- trace JSON labels `metric_frequency_basis="legacy_control_hz"`;
- future absolute-Hz paper comparisons must choose the physical fields or
  declare the legacy basis.

The existing strict `xfail` remains correct because the plant/contract mismatch
itself still exists. R261 fixes trace provenance and physical observability, not
the underlying plant choice.

## Finding 2 — failed partial traces could be scored

### Root cause

`paper_path.run_scenario()` broke out of its loop on `tds_failed` but did not
copy that status into its returned record. The ranker's existing failure guard
therefore could not fire. `summary.score_trace_files()` independently loaded
the shortened trace and computed `cum_rf`, for which a shorter accumulation can
look artificially good.

### Fix

New records persist:

- `tds_failed`
- `completed`
- `requested_steps`
- `n_steps`

The canonical summary now raises `ValueError` before scoring a trace that is
failed, explicitly incomplete, empty, or whose `n_steps` disagrees with its
payload.

### Historical scope

This is a reachable correctness hole, not evidence that a current headline is
wrong. The audit did not find a current full-evaluation trace with
`n_steps < 150`; R261 therefore makes no retroactive contamination claim.

## Finding 3 — recurrent Bellman targets skipped realised history

### Root cause

For the first loss transition after burn-in, the old update sequence was:

1. warm target hidden state through `obs[t-1]`;
2. directly query the target actor/critic with `next_obs[t]`;
3. reuse the hidden state returned by the hypothetical
   `(next_obs[t], target_action[t])` critic branch.

This omitted realised `(obs[t], action[t])` from the first target and caused
later critic targets to follow hypothetical target-action history rather than
the replay trajectory.

### Fix

- Target actor is aligned through current `obs[t]` before the first
  `next_obs[t]` query.
- Target critics advance on each realised `(obs[t], action[t])`.
- The next-state target query branches from that state and discards its returned
  hidden state.
- WarmH0 target actors initialise from the real sequence's first observation,
  not `next_obs[0]`.

The exact alignment regression covers:

1. TD3-LSTM
2. TD3-LSTM-HReg
3. TD3-LSTM-WarmH0
4. TD3-AFE-LSTM
5. TD3-QR-LSTM
6. TD3-QR-LSTM-HReg
7. TD3-QR-AFE-LSTM
8. TD3-WarmH0-QR-LSTM
9. TD3-WarmH0-QR-AFE-LSTM

### Scientific implication

Historical checkpoints still faithfully reproduce the legacy implementation
and their measured trajectories remain evidence about those models. They must
not be described as having been trained with the corrected recurrent Bellman
target. Any claim that the intended corrected TD3-LSTM algorithm reaches the
same plateau requires retraining; R261 itself contains no such experiment.

## Pre-registered gate evaluation

| Gate | Outcome |
|---|---|
| Real ANDES 60 Hz vs contract 50 Hz | **CONFIRM** |
| Failed trace is scoreable | **CONFIRM → FIXED** |
| Tagged recurrent target skips current transition | **CONFIRM → FIXED** |
| Preserve historical V4/checkpoint semantics | **PASS** |
| No performance/SOTA interpretation | **PASS** |

## Verification

| Layer | Result |
|---|---|
| Windows full pytest | **304 passed, 3 skipped, 1 expected xfail** |
| WSL full pytest with real ANDES | **317 passed, 1 expected xfail** |
| WSL live ANDES environment subset | **16 passed** |
| Recurrent exact-alignment variants | **9 passed** |
| Ruff (`src tests scripts`) | **all checks passed** |
| Python compileall | **passed** |
| `git diff --check` | **passed** |

The expected xfail is the deliberately unresolved plant/contract 60/50
frequency mismatch. No `[DEBUG-*]` instrumentation or throwaway harness remains.

## Claims

- CLM-0495 — recurrent TD-target alignment correction.
- CLM-0500 — failed/partial trace propagation and rejection correction.
- CLM-0505 — dual frequency-basis decision and live verification.

## Questions opened

- None. A physical-Hz canonical rebaseline is intentionally deferred as a
  separate performance round, not smuggled into this correctness round.

## Questions closed

- None.

## Questions advanced

- Q-0004 remains open. R261 adds live WSL coverage and preserves V4 legacy
  frequency traces, but it does not by itself prove the entire AD-01 refactor
  is `1e-9` identical across all recorded fields.

## Cross-references

- R89 verdict / CLM-0171 — original cached 60/50 finding.
- ADR-0002 — paper-strict versus paper-faithful-modified terminology.
- ADR-0006 / NOTE-0024 — dual frequency reporting and V4 compatibility.
- CLM-0014 — locked NaN/`tds_failed` ranker guard.
- NOTE-0011 / NOTE-0012 — original recurrent update design.
- `probes/r261_wsl_correctness.json` — machine-readable probe summary.

## 给 PI 的话

**这轮干了啥**：不是继续调参，而是把审计里最可能动摇结论的三件事搬到
WSL 真 ANDES 和确定性回归里逐一验证。

**结果一句话**：三件事都是真的；失败轨迹和 LSTM target 已修，60/50 Hz
没有偷改历史 V4，而是按 ADR-0006 同时输出 legacy 与 physical 两套明确标定。

**最重要的科研影响**：过去 LSTM checkpoint 的观测结果仍然是真的，但它们
属于“legacy misaligned recurrent target”实现；要判断修正后的 TD3-LSTM
是否仍有同样 plateau，必须另开训练 round，不能用本轮测试结果代替。

**默认下一步**：先做一个小规模、预注册的 corrected-vs-legacy 同种子训练
对照，再决定是否值得重跑完整多种子基准；物理频率则先离线重评分 R261+
双字段 trace，确认对 11-axis 排名的影响后再升级 canonical metric。
