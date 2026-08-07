---
round: R343
state: aborted
manuscript_line: icems2026
opened: '2026-08-06'
closed: '2026-08-06'
supersedes_rounds: []
superseded_by_round: null
abort_reason: User reprioritized decoupling-marl-model-first after the plumbing canary;
  formal evaluation was not released, all artifacts are preserved, and the host reservation
  is released.
superseded_note: null
---
# R343 plan — formal-manifest recovery

**Opened**: 2026-08-06
**Driver**: Recover the R342 pre-physical canary failure without retraining,
redrawing the bank, or modifying its immutable attempt.
**Parent**: R342 aborted engineering attempt; CLM-0905 remains unchanged.

## TL;DR

Workload: `evidence`. Add one successor adapter whose prepared manifest is
accepted by the exact worker verifier. Reuse hash-verified R342 checkpoints,
screen traces and bank. Run a no-output rehearsal, create a new seal, run the
same sixteen-worker plumbing canary, then stop before formal evaluation.

## Snapshot at plan-time (oracle as of 2026-08-06)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0090 [opened R341] Can the fresh-qualified predictor support a deterministic physical bridge before any distributed or learning experiment?

## Recently Closed (last 3)

- Q-0089 closed-positive @ R341, by CLM-0900 — Does the selected predictor preserve its registered waveform envelope on an untouched operating-point bank?
- Q-0087 closed-partial @ R339, by CLM-0890 — Which location-dependent input dynamics explain the upstream-load mismatch before any bridge repair?
- Q-0088 closed-negative @ R338, by CLM-0905 — On the fixed four-VSG path, does a neighbour-only distributed edge residual add guarded value beyond the selected causal edge controller and remain non-inferior to a matched joint-observation single actor?

## Methodology

### Files and interfaces

- Create `scripts/run_r343_limited_reverse_recovery.py`: new manifest builder,
  exact runtime verifier, R343 canary/formal routing and host orchestration.
- Create `tests/test_r343_limited_reverse_recovery.py`: real prepared-seal to
  worker-verifier integration test plus canary provenance/release tests.
- Reuse read-only `scripts/run_r342_limited_reverse_residual.py`,
  `results/r342_limited_reverse_training`, `results/r342_fresh_bank`, and all
  R337 beta-zero checkpoints. Do not modify any R342 source or artifact.

The adapter produces these stable interfaces:

```python
def prepare_formal_seal(manifest_path: Path, out_dir: Path) -> str: ...
def verify_formal_seal(manifest_path: Path, expected: str) -> dict[str, Any]: ...
def run_canary_worker(manifest_path: Path, expected: str, *, shard_index: int,
                      shard_count: int) -> None: ...
def verify_canary(manifest_path: Path, expected: str) -> str: ...
```

The seal follows the inherited verifier schema exactly: top-level
`training_summary_sha256`, nested `screen.summary_sha256`, frozen R342 arms,
same bank hash, same thresholds, and `formal_trace_count_at_freeze=0`.

### Test-driven slices

- [ ] RED: a seal prepared by the recovery adapter is rejected or unavailable
  when passed to the exact configured worker verifier.
- [ ] GREEN: add only the R343 adapter and top-level training hash required for
  the prepared-seal/worker-verifier round trip.
- [ ] RED/GREEN: reject a manifest whose training, screen, bank, checkpoint or
  controller-contract hash drifts.
- [ ] RED/GREEN: require sixteen completed, overlapping, isolated canary
  records and forbid performance use.
- [ ] Regression: Windows and WSL focused suites pass before rehearsal.

### Execution stages

1. Same-path rehearsal: source/parent hashes, installed ANDES/case, exact
   prepared-payload verification in memory, output absence, process/thread
   budget. It creates no attempt, seal or physical trace.
2. Create-only R343 seal and attempt.
3. Sixteen workers run one fixed 15-step controller cell each. Persist logs
   and records atomically. No performance aggregation or scientific reading.
4. Verify overlap, scratch isolation, hashes and completion. Stop at canary
   PASS. Formal evaluation requires a later explicit release.

## Gate

- `MANIFEST-ROUNDTRIP-PASS`: the same prepared seal is accepted by the exact
  worker verifier before any ANDES launch.
- `PHYSICAL-CANARY-PASS`: 16/16 records complete, overlap, use unique scratch
  directories, retain one native thread each and create no formal trace.
- Any hash, schema, launcher, ANDES or canary failure: preserve artifacts,
  abort R343, no retry.
- PASS authorizes only the already frozen R342 formal matrix. It is not an
  algorithm result and changes no manuscript claim.

### Outcomes

- Exact manifest verifier rejects the prepared successor seal:
  `MANIFEST-ROUNDTRIP-FAIL`; abort before ANDES, no retry.
- Manifest passes but any canary record fails completion, overlap, isolation,
  provenance or hash checks: `PHYSICAL-CANARY-FAIL`; abort, no retry.
- All sixteen canary records pass: `PHYSICAL-CANARY-PASS`; stop and require a
  separate user release before formal controller evaluation.
- Later formal outcomes, if explicitly released, use the unchanged R342
  `LIMITED-REVERSAL-*` decision tree; no R343 canary field enters that tree.

The frozen beta-zero baselines remain the five R337 runs
`distributed_prior_s421`, `distributed_prior_s463`,
`distributed_prior_s509`, `distributed_prior_s557`, and
`distributed_prior_s601`.

## Formal launch contract

- formal_entry: `python scripts/run_r343_limited_reverse_recovery.py execute-canary`
- formal_release_entry: `python scripts/run_r343_limited_reverse_recovery.py execute-formal`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r343_limited_reverse_recovery.py rehearse`
- rehearsal_scope: same-pre-attempt-path; no attempt, seal or physical output
- rehearsal_checks: source_hash,parent_hash,installed_package,installed_case,manifest_roundtrip,output_absence
- wsl_python_processes: 16
- native_threads_per_process: 1
- capacity_evidence: `memory/rounds/R343/host_capacity.json`
- host_process_budget: 16
- other_reserved_processes: 0

## 资产保护契约

标题、R338 结论、R342 文件、五个新模型、五个旧模型、24 个场景、动作
公式、阈值、随机种子和分析器全部冻结。只新增 R343 适配器、测试、容量
快照、排练、封存、并发小样和后续正式输出。论文正文和现有 claim 不改。

## Cross-references

- `memory/rounds/R342/formal_failure.json`
- `memory/rounds/R342/formal_seal.json`
- `results/r342_limited_reverse_training/training_matrix_summary.json`
- `results/r342_fresh_bank/screen_summary.json`
- `results/r342_fresh_bank/formal_bank.json`
- `memory/claims/CLM-0905.md`
