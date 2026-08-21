---
round: R453
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-20'
closed: '2026-08-20'
supersedes_rounds:
- R452
superseded_by_round: null
abort_reason: null
superseded_note: R452 executed all 8,424 trajectories successfully but its aggregate
  population named joint_endpoint_eligible added an unregistered valid=true filter.
  R453 reuses only the immutable verified R452 shards and repairs the offline aggregation
  semantics.
---
# R453 plan — M5 聚合语义修复（复用 R452 不可变分片）

**Opened**: 2026-08-20
**Driver**: R452 的 68 个分片、8,424 条轨迹和全部 sidecar 均通过，
但 `_summarize_profile_rows` 把未登记的 `valid=true` 过滤加入
`joint_endpoint_eligible_count` 与 conditional minima population；本轮只修复
聚合语义并重新封存，不重复物理仿真。
**Parent**: R452 plan/seal/shards/algorithm audit；CLM-1355 (R439)、
CLM-1365 (R441)、advisory M5。

## TL;DR

Workload: `evidence`。Offline aggregation-only successor. Verify every R452
shard identity and sidecar, reconstruct the four complete candidate tables,
separate endpoint-only from valid-and-endpoint populations, independently
recompute guards and the four-objective Pareto fronts, and emit a new hashed
R453 decision artifact. No ANDES or WSL execution, training, candidate change,
threshold change, or trajectory retry is authorized.

## Snapshot at plan-time (oracle as of 2026-08-20)

- R452 terminal state: aborted, `CANARY-INVALID`.
- R452 immutable execution inventory: 68 shards; 1,400 candidate rows; 8,400
  candidate trajectories; 24 static trajectories; zero execution errors.
- R452 post-aggregate audit:
  `memory/rounds/R452/algorithm_audit.json` (SHA-256
  `6d692e72a8e0d160fc3bcd69eb16e0412c4d0a69c86f2d7d4e5a9dc48b07d723`).

## Methodology

**Frozen repair contract:**

- Read only R452's 68 hashed shard payloads and its sealed runner/source
  inventory. Reject missing, extra, duplicate, unhashed, hash-drifted, wrong-
  round, wrong-profile, nonfinite, or execution-invalid payloads.
- Preserve all 350 generated IDs per profile and the exact candidate sequence
  SHA-256
  `6f505fa569e5a22d8163da44a38292fecc433180cff7640fce6fff4984433962`.
- Recompute every guard from each stored full summary and fresh stored static
  reference. Thresholds remain: both endpoint improvements at least 5%; three
  common metrics no worse than +3%; action RMS and total variation no worse
  than +10%; saturation at most 5%; `joint_guard_feasible` also requires
  validity.
- Define and store two explicit populations:
  `endpoint_only_eligible` = both endpoint thresholds, without validity; and
  `valid_endpoint_eligible` = endpoint-only plus the full valid flag.
  `joint_endpoint_eligible_count` is the endpoint-only count. Conditional
  minima are stored for both populations; the primary advisory observable is
  the endpoint-only population, exactly as R452's sealed plan stated.
- Recompute the Pareto set among valid + common-clean + saturation-clean rows
  over minimized `(E_d/E_d0, E_x/E_x0, action_rms/action_rms0,
  action_tv/action_tv0)`, retaining objective ties and duplicate IDs.
- Store a parent comparison proving which R452 fields were unchanged
  (`joint_guard_feasible_ids`, Pareto fronts, classification) and which were
  repaired (eligible counts/population labels).

## Gate

### Outcomes

- `GUARD-CLEAN-JOINT-HEADROOM-IN-GRID`: all four profiles contain at least one
  recomputed `joint_guard_feasible` ID.
- `PARTIAL-GUARD-CLEAN-JOINT-HEADROOM-IN-GRID`: one to three profiles do.
- `NO-GUARD-CLEAN-JOINT-HEADROOM-IN-GRID`: none do.
- `CANARY-INVALID` takes precedence on any parent/shard/source/hash/identity/
  finiteness/completeness mismatch, any disagreement between freshly
  recomputed row guards and stored raw summaries, or any output preexistence.
- A coincidentally unchanged R452 classification is not evidence by itself;
  only the new R453 hashed artifact can close M5.

## Formal launch contract

- formal_entry: `python scripts/run_r453_m5_aggregate_repair.py execute`
- rehearsal_command: `python scripts/run_r453_m5_aggregate_repair.py rehearse`
- rehearsal_scope: same-pre-attempt-path parent/source/shard verification plus
  pure boundary, population-separation, conditional-minimum, and Pareto-tie
  probes; creates no formal output.
- rehearsal_checks: source_hash, parent_hash, all 68 shard sidecars, exact ID
  inventory, output_absence, guard boundaries, population separation, Pareto
  ties.

## 资产保护契约

- Read-only: all R452 plan/seal/audit/results/shards and all earlier
  R439/R441 assets; no edit to the sealed R452 runner or test.
- New only: R453 runner/test/rehearsal/seal/result/feed/claim/verdict and normal
  manifest/line pointers after a valid close.
- No physical rerun, training, tuning, learner/controller/schedule change,
  threshold change, profile/scenario change, or result-driven retry.

## Cross-references

- R452 aborted audit; CLM-1355; CLM-1365; advisory M5.
