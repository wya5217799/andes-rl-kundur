---
round: R334
state: completed
opened: '2026-08-04'
closed: '2026-08-04'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R334 plan - publication-evidence correction for physical PQ identification

## TL;DR

Repeat the exact R333 bank and thresholds under a corrected seal. Hash all
local runtime dependencies; record inherited reward diagnostics but forbid
their use; wrap the unchanged R333 helper and rules with strict R334 identity.
Do not tune from R333 outcomes or run a controller.

## Authority and workload

- Direct question: `memory/questions/Q-0085.md`, still open after process
  correction `CLM-0875` withheld the R333 physical result.
- Scientific authority: unchanged R333 bank/thresholds, immutable R316/R329,
  R332 blocker, and installed ANDES 2.0.0. R333 outcomes are diagnostic only.
- Workload: `evidence`, because R334 creates new physical trajectories and may
  dispose Q-0085. The conference title remains byte-for-byte unchanged.
- Research Supervisor route: correction of one evidence-chain defect only; no
  new literature or algorithm route. Ask Matt route: diagnosis-driven minimal
  repair with focused red tests before any formal execution.

## Methodology

Use one red-green evidence slice without changing physical or scientific code.
Tests cover source omission, reward non-use, identity-only translation, and
binding restoration. Dry-run the seal, obtain two reviews, then execute once.

## Frozen scientific bank

- Operating points remain exactly HS0 and HS1 with per-device M/D
  `177.5/88.75` and `202.5/101.25`, tie R/X scales `1.10/1.35`, and initial
  SOC `0.41/0.51`.
- Existing device `PQ_Bus14`; exactly six records = two points crossed with
  zero, positive, and negative active-load perturbations. The signed amplitude
  remains `+/-0.05` system p.u. on the 100-MVA system base; reactive power is
  unchanged and negative-load crossing is forbidden.
- Four absolute pre-setup `Alter` events apply P/Q at 0.5 s and restore their
  exact pre-event values at 1.5 s. Event identifiers remain the immutable R333
  helper's identifiers and have no round-identity role. Use five 0.2-s active
  periods, twenty 0.2-s recovery periods, and five TDS subdivisions per period.
- Inputs remain zero M/D actions and zero ESD1 power requests. Line_8 and G4
  remain in service. Record actual tie R/X, M/D, SOC, all requested/projected/
  internal/achieved ESD1 power, PQ status and replacement pointers, event
  callbacks, solver state, and exact time grid.
- The immutable R316 realization and prospective map remain
  `d_node = -delta_P_load * [0, 0, 1, 0]`. No refit, scale correction, time
  shift, sign flip, output selection, threshold change, case selection, or
  outcome-driven repair is permitted.

## Unchanged scientific rules

- Require exact PQ write/readback/restoration within `1e-12` system p.u.,
  correct common-frequency sign, and signal-to-baseline-drift energy ratio at
  least `10` for every signed record.
- Define the signed-pair diagnostic exactly as the normalized L2 midpoint
  residual `||0.5(r+ + r-)||_2 / [0.5(||r+||_2 + ||r-||_2)]`; require at most
  `0.10` at each point. Passing supports approximate odd symmetry for this one
  signed pair, not local or global linearity.
- Reuse the R316 finite-bank envelope without change: total NRMSE at most
  `0.15` and global-peak-normalized maximum vector residual at most `0.20` for
  every signed record.
- `INVALID-PHYSICAL-DISTURBANCE-IDENTIFICATION`: any identity, source,
  inventory, execution, restoration, zero-actuator, numerical, replay,
  diagnostic-reward, or exclusion guard fails; interpret no response metric.
- `BLOCK`: execution is valid but observability, sign, signed-pair, or frozen
  equivalence rules fail. `QUALIFY`: every validity and scientific rule passes.
  `ALLOW` remains unreachable because one physical column cannot validate the
  arbitrary four-node R329 disturbance object.

## Evidence correction contract

- Preserve R333 executable scientific sources (helper, probe, adapter, tests)
  and result artifacts byte-for-byte. Its plan and Q-0085 lifecycle record may
  differ from their pre-execution hashes because closure appended disposition
  history. Add only an R334 adapter, pure classifier wrapper, and focused tests.
- The seal must hash the R334 plan/question/adapter/probe/tests, the inherited
  R333 adapter/probe/helper, `andes_scratch.py`, `artifact_io.py`, and every
  Python file under `src/andes_rl_kundur` as a conservative repository-local
  runtime dependency superset. It must also pin the installed ANDES source
  inventory and case-file hash used by the runtime.
- The seal and every formal artifact must register:
  `reward_diagnostics_computed=true`, `reward_diagnostics_stored=true`, and
  every use flag for action, fitting, selection, training, classification, and
  claim as false. The inherited trace may retain its existing reward fields,
  but the classifier must not read their presence or values. Publication audit
  verifies storage separately from the scientific decision.
- The R334 classifier must first validate original R334 identities and the
  reward/source contract, then translate only the round identity in an in-
  memory copy to invoke the unchanged R333 decision rules. The original
  execution artifact remains R334. Any translation of data, thresholds,
  inputs, predictions, events, records, or scientific fields is forbidden.
- Formal attempt, execution, provenance, manifest, and analysis remain create-
  only with sidecars. The formal-attempt marker precedes the first trajectory;
  interruption forbids automatic retry.

## Verification and stopping conditions

- Run preflight before implementation. Write focused red tests for missing
  source closure, R334 identity, reward-boundary fields, in-memory identity-only
  delegation, classifier independence from reward-field presence and values,
  restoration of inherited module bindings after success or exception, strict manifest,
  create-only behavior, and deterministic two-pass analysis.
- No physical canary is required because the inherited R333 helper and
  `_run_record` mechanics are immutable and already passed the R333 canary;
  R334 changes only prospective evidence binding and identity wrapping. Use
  Windows-host unit tests and a temporary prepare/load-seal dry run instead.
- Before sealing, run focused tests, lint, compilation, source-closure checks,
  preflight, and two independent pre-seal reviews. Then seal, run the formal
  six-record bank once in WSL, analyse twice deterministically, and never amend
  the contract after outcome access.
- Complete independent evidence and power-system publication audits before any
  finding registration. A failed audit aborts R334 and leaves Q-0085 open.
- Stop after the corrected disturbance judgment. No controller, headroom test,
  distributed runtime, reward design, training, EVAL, topology, stability,
  safety, or title-result claim is authorized.
