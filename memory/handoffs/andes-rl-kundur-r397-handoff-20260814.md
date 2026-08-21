# Handoff: converter-VSG P/Q-decoupling line after R397 (PPVSM1 signed-authority stop)

## Purpose

Continue the `converter-vsg-pq-decoupling` manuscript line from its current
state. R397 has just closed the signed P/Q authority gate with a valid
`STOP-PPVSM1-SIGNED-AUTHORITY` (CLM-1130). The line is now stopped before
droop-slope matching and before any controller work. This handoff is
navigation only: numbers, hashes, and evidence live in the cited artifacts.

## Workspace and authority

- Repository (current session): `E:\Projects\andes-rl-kundur` (keep the
  dirty worktree intact; nothing from this line is committed).
- Selected line: `converter-vsg-pq-decoupling` (write scope = that line
  only). Stage: `ppvsm1-signed-authority-stop`.
- Other active line: `decoupling-marl-model-first` — manuscript-closure
  only, experiment side frozen (ADR-0018).
- Bootstrap: `$env:PYTHONUTF8='1'; python memory/tools/session_context.py --json --line converter-vsg-pq-decoupling`
- Process canonical: `skills/kundur-round/SKILL.md`; round/claim IDs only
  via `reserve_round.py --strict-no-active --line ...` and
  `reserve_claim.py --round ...`.

## What was completed this session (pointers only)

- R397 signed P/Q authority gate for the two-unit PPVSM1 cell ->
  `STOP-PPVSM1-SIGNED-AUTHORITY`: claim `memory/claims/CLM-1130.md`,
  feed `paper/converter_vsg_pq_decoupling/reports/R397.md`, Q-0111 closed
  negative. Headline: the nine-arm bank is fully admissible (exact receipts,
  signed responses 0.0355-0.0466 pu, paired separations 0.0712-0.0931,
  solver/envelope/finite/diagnostics all pass), but target attribution fails
  on the two PPVSM1_1 Pref arms (PPVSM1_2's achieved Pe magnitude exceeds the
  target's own; margins -0.00354/-0.00315 vs the 2e-4 floor).
- New seams: `src/andes_rl_kundur/evaluation/ppvsm1_signed_authority_gate.py`
  (pure classifier + frozen contract),
  `scripts/run_r397_ppvsm1_signed_authority_gate.py` (bank runner),
  `tests/test_ppvsm1_signed_authority_gate.py` +
  `tests/test_r397_ppvsm1_signed_authority_gate.py`. One post-seal test-only
  fix: the runner-test lifecycle assertion now checks the closed state
  (plan state=completed, Q-0111 closed-negative by CLM-1130); the sealed
  scientific record is untouched.
- Repo-hygiene fix: root pollution by in-process real-ANDES tests
  (`kundur_full_out.*`) is now backstopped by an autouse teardown fixture
  in `tests/conftest.py` and the confirmed polluter
  (`tests/test_v4_env_regression.py`) got a module-level
  `monkeypatch.chdir(tmp_path)` isolation. The
  `test_real_checkout_passes_repository_health_cli` test is green again.

## Current state snapshot

- `repo_health.py check --no-baseline`: 0 active findings.
- `validate.py`: OK (391 claims, 111 questions, 37 pre-existing warnings).
- `round_preflight.py R397`: OK to launch (post-rehearsal).
- Round state: R397 completed; no active rounds.
- Cold start for the line: mode=manuscript, stage=ppvsm1-signed-authority-stop,
  no artifact alerts.
- Full suite (WSL) at close: 1905 passed / 12 failed; the 12 failures are
  pre-existing and owned by other lines (QP/estimation tests with
  cvxopt-vs-kvxopt expectations + the andes_scratch_launcher wsl-path
  test). The suite leaves the root clean (conftest backstop + v4 cwd
  isolation).

## Environment facts (resume without rediscovery)

- ANDES is WSL-only: `/home/wya/andes_venv/bin/python`, ANDES 2.0.0.
- **WSL invocation gotcha (new)**: do NOT run rehearsals/executes through
  `wsl.exe bash -lc "python ... run_r... ..."` — the wrapper bash's cmdline
  embeds the research command and `other_research_python_processes()`
  flags the wrapper as a competing process, failing the rehearsal gate.
  Write a small script file (`tmp/*.sh`, LF endings) and invoke
  `wsl.exe bash /mnt/e/Projects/andes-rl-kundur/tmp/<script>.sh`; the
  andes_scratch launcher execs itself on POSIX, so the wrapper cmdline stays
  clean.
- The R393 module owns `installed_runtime`/`_inventory`/`_capture_trace`
  four parent levels down the runner chain (run_r397 ->
  parent_runner.parent_runner.parent_runner.parent_runner); probe attribute
  levels before reuse (see the R397 runner's `R393_PARENT` alias).
- PPVSM1 has no `_setpoints` registry: apply reference steps by direct
  writes to `system.PPVSM1.Pref.v`/`Qref.v` array elements (the same
  mechanism `RenGen.set_setpoint` uses). R397's receipts prove it
  propagates.
- The line-state snapshot algorithm is `_hash_input` in
  `src/andes_rl_kundur/repo_governance.py`:
  `sha256(b"directory-tree-v1\0" + relpath + b"\0" + raw_digest per
  sorted file)`; file inputs are plain file sha256. Recompute with that
  exact algorithm when refreshing `ARTIFACTS.json`.
- **Navigation byte budget is razor-thin**: LINE.md + route_contract.md +
  ARTIFACTS.json currently total 24557 bytes against the 24576 limit
  (19 bytes of margin). Any addition to LINE or the route contract needs an
  offsetting trim.
- Round-runner bug classes caught by this session's smoke tests (keep the
  rehearsal canary): contract inventory shapes vs builder output, parent
  chain attribute depth, capture-trace start-sample slicing vs strict
  post-start schemas. The full-bank rehearsal canary (R396 lesson) caught
  the inventory mismatch before the seal — keep it for every successor.

## Next steps (in order; each needs explicit PI authorization)

1. **No successor is authorized.** The PPVSM1 branch is stopped by R397
   before droop-slope matching and before any controller/decoupling/learning
   work. Any continuation (droop-slope verification vs the stopped REGF2
   object, a revised PPVSM1 cell/topology/operating point, or four-unit
   scaling) is a NEW prospective route decision and needs a fresh
   registered round with frozen plan + rehearsal + seal.
2. Optional housekeeping: codify the R393-R395/R397 instrumentation lessons
   (the WSL wrapper-cmdline pollution, chain-depth probes) into CLAUDE.md /
   tools; the conftest backstop is already codified.
3. If the user consults GPT again on the decoupling-marl-model-first line,
   every new `working/` file there must be registered in that line's
   ARTIFACTS.json or repo_health goes red again.

## Non-negotiable boundaries (unchanged)

- R390 and R393/R394/R395 are immutable analysis-invalid evidence; no
  repair, retry, or reinterpretation.
- Closed rounds are never re-executed; a post-seal defect aborts the round
  and requires a separately authorized science-identical successor.
- R397's STOP is a formulation-level attribution failure at one operating
  point: no instability, technology-class-rejection, decoupling-value, or
  controller claim is authorized by it.
- Preserve the Kundur network and the ANDES 2.0.0 platform; the two-unit
  cell is frozen; four-unit scaling is a separate later gate.
- 给 PI 的话: three-part plain Chinese only; the forbidden-jargon list lives
  in `memory/tools/validate.py` (`PI_PROJECT_JARGON_TERMS`).

## Suggested skills

- `skills/kundur-round/SKILL.md` — repository process canonical.
- `ask-research-supervisor` — Mission mode for the next long task.
- `experiment-efficiency-gate` — before any newly authorized formal ANDES
  execution.
- `audit-manuscript-evidence` + `publication-gate.md` — at claim-bearing
  closes.
- `diagnosing-bugs` — tight-loop discipline for instrumentation defects.

## Redaction

No API keys, credentials, or personal secrets were exchanged or stored.
