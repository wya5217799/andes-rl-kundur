---
round: R340
state: completed
manuscript_line: decoupling-marl-model-first
opened: '2026-08-04'
closed: '2026-08-05'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R340 plan - fresh nonlinear validation of the input-aware predictor

**Opened**: 2026-08-04
**Driver**: Resolve the model gate before any controller, distributed-agent, or learning work.
**Parent**: CLM-0890; Q-0089

## TL;DR

R340 tests the unchanged R339 separate-input, order-12 construction on two
previously unexecuted operating points and 66 prospectively fixed nonlinear
records. For each new point, the descriptor-derived candidate is built only
from that point's equilibrium Jacobians, persisted create-only, and hashed
before any new trajectory is opened. No nonlinear trajectory is used for
fitting, selection, repair, or scheduling. A valid failure blocks the bridge;
a valid pass admits only a later deterministic physical-bridge question.

The conference-paper title remains exactly `Decoupling-Oriented Coordination
of Paralleled VSGs With Multi-Agent Reinforcement Learning`. R340 neither
tests nor supports that title, coordination, distributed agents, or learning.

## Snapshot at plan-time (oracle as of 2026-08-04)

- Q-0089 is the only selected-line question in scope.
- R339 is complete with classification `ALLOW-CANDIDATE`; its HS0 and HS1
  records were exposed before Q-0089 opened.
- R338 belongs to `icems2026`, is not executing, and remains immutable.
- No ANDES or research Python process was active at the R340 capacity snapshot.

## Methodology

The following scientific contract, construction order, bank, metrics, gates,
and first-failure outcomes are frozen before any R340 physical execution.

### Fixed scientific contract

#### Candidate construction before validation

Preserve every R339 source, threshold, coordinate convention, sample timing,
model order, and normalization choice. At each new operating point, extract
the four control and four physical-load columns independently using central
differences at `1e-4`, `1e-5`, and `1e-6` system p.u. Fold exact zero-time-
constant states into the algebraic block, require the same exact named-state
reconciliation and Schur guards as R339, discretize at `0.2 s` with end-of-
held-interval observations, then construct one joint order-12 ERA realization
from 25 full-order Markov samples using eight block rows and eight block
columns, with no pole projection.

Both point realizations, their construction guards, and their exact payload
hashes must be written create-only to `candidate_models.json` by a sealed
construction phase. A second validation seal must then bind the exact
`candidate_models.json` hash before the first nonlinear record begins. The
validated object is the prospectively fixed R339
construction procedure scheduled only by the declared operating point; R340
does not claim one operating-point-invariant realization. Any descriptor or
construction failure stops before trajectories with `BLOCK-CONSTRUCTION`.

#### Untouched operating-point bank

The two new points are:

- HV0: `vsg_m_device=190.0`, `vsg_d_device=95.0`, `tie_rx_scale=1.22`,
  `initial_soc=0.46`.
- HV1: `vsg_m_device=220.0`, `vsg_d_device=110.0`, `tie_rx_scale=1.45`,
  `initial_soc=0.56`.

At each point execute one zero-load reference and the Cartesian product of:

- physical-load positions: `PQ_0`, `PQ_1`, `PQ_Bus14`, `PQ_Bus15`;
- waveforms: `held_pulse_unit=[0.6,1.0,1.0,1.0,0.6]` and
  `two_pulse_unit=[1.0,1.0,0.0,0.0,0.6,0.6]`;
- absolute amplitudes: `0.03` and `0.07` system p.u.;
- signs: positive and negative.

This is 32 disturbed records plus one zero reference per point, 66 records in
total. Each profile is zero-padded to 1000 samples, giving a 200-second
validation horizon. The order-12 construction remains fixed to the R339
25-sample Markov contract; the persisted state-space predictor is then run
open-loop over the full 1000-sample horizon. This long tail tests decay and
slow drift rather than duplicating deterministic records. Event start,
exact-event-row
semantics, substeps, physical readback, frequency coordinates, system and
device bases, topology guards, and reward non-use remain those of R336/R339.
The bank, order, worker ownership, and limits are sealed before execution and
cannot be changed from outcomes.

#### Prediction and metrics

For each disturbed record, subtract the same-point nonlinear zero reference.
Feed the exact physical load sequence into both the full sampled descriptor
model and the persisted order-12 candidate. Control-input columns remain zero.
Compute over all 1000 samples, separately for full-versus-nonlinear and
order12-versus-nonlinear:

- total NRMSE `||prediction-truth||_F / max(||truth||_F, 1e-15)`;
- peak-normalized vector residual using the maximum four-coordinate vector
  norm over time with denominator at least `1e-15`.

Report the registered `0.50--0.62 Hz` and `0.72--0.86 Hz` modal bands only as
descriptive attribution. They cannot change a model, threshold, or outcome.

## Gates and stopping outcomes

Every one of the 64 disturbed records must satisfy, for both full sampled
model and order-12 candidate:

- NRMSE at most `0.15`;
- peak-normalized vector residual at most `0.20`.

All 66 nonlinear records must also pass the unchanged R336 physical validity
guards, including exact event inventory/readback, baseline restoration, zero
actuator use, topology service, finite state/algebraic values, zero exit code,
and algebraic residual at most `1e-6`.

Apply the first applicable outcome and stop:

- `INVALID`: seal, source, parent, runtime, process, event, physical validity,
  persistence-order, finite-value, or deterministic-replay guard fails.
- `BLOCK-CONSTRUCTION`: a new-point equilibrium descriptor cannot reproduce
  the frozen R339 construction contract before trajectories.
- `BLOCK-FULL-LINEARIZATION`: construction is valid but the full sampled
  descriptor fails any registered nonlinear-record limit.
- `BLOCK-REDUCTION`: full sampled descriptor passes but order 12 fails any
  registered nonlinear-record limit.
- `ALLOW-MODEL-GATE`: construction, full sampled descriptor, and order 12 pass
  all records and limits.

There is one create-only formal construction attempt and, only if construction
passes, one create-only formal trajectory attempt. Neither phase has a retry.
A valid failure is evidence and is not repaired in R340. Stop before
controller execution, feedback, closed loop,
distributed runtime, reward design, agent creation, training, evaluation,
topology change, stability/safety testing, or manuscript-result drafting.

## Engineering seam and test-first return contract

The public runner seam must expose:

1. a machine-readable 66-record contract;
2. a deterministic schedule proving both candidate hashes precede all
   trajectory records while using at most sixteen whole-host Python processes;
3. a pure first-failure classifier and per-record metric analysis;
4. create-only construction seal/candidate artifacts followed by a distinct
   validation seal that binds the candidate hash, then create-only execution,
   provenance, manifest, and analysis artifacts with deterministic replay.

Tests must first fail on this seam, then pass after the smallest implementation.
Any controller, agent, reward, training, or evaluation import/call is forbidden.

## Formal launch contract

- construction_prepare: `python scripts/run_r340_fresh_model_validation.py prepare-construction`
- construction_rehearsal: `python scripts/andes_scratch.py scripts/run_r340_fresh_model_validation.py rehearse-construction --expected-sha256 <construction-seal>`
- construction_entry: `python scripts/andes_scratch.py scripts/run_r340_fresh_model_validation.py construct --expected-sha256 <construction-seal>`
- validation_prepare: `python scripts/run_r340_fresh_model_validation.py prepare-validation --candidate-sha256 <candidate-models>`
- validation_rehearsal: `python scripts/andes_scratch.py scripts/run_r340_fresh_model_validation.py rehearse-validation --expected-sha256 <validation-seal>`
- formal_entry: `python scripts/andes_scratch.py scripts/run_r340_fresh_model_validation.py execute --expected-sha256 <validation-seal>`
- construction_rehearsal_scope: source/runtime/case/equilibrium/descriptor path;
  no formal artifact and no new nonlinear trajectory
- validation_rehearsal_scope: sealed source/runtime/case/candidate/output-
  absence checks; no new nonlinear trajectory and no formal-attempt artifact
- wsl_python_processes: 16
- native_threads_per_process: 1
- capacity_evidence: `memory/rounds/R340/host_capacity.json`
- host_process_budget: 16
- other_reserved_processes: 0

The measured host has 16 physical cores and the same host already passed a
16-process single-threaded R339 canary without swap. R340 assigns the parent
one deterministic job stream and fifteen forked worker streams. The entire
host budget, including the parent, never exceeds 16 Python processes. A worker
reuses its isolated process for multiple records; record scratch directories
remain distinct. Utilization is pursued only through registered scientific
jobs, never synthetic load. Thirty-two logical processors are not treated as
thirty-two independent physical simulation cores: the measured one-process-
per-physical-core design avoids oversubscribing shared execution resources.
Scaling the measured R336 25-step cost to 1000 steps gives an advance wall-
clock estimate of 11--15 minutes for the 66-record bank. Rich per-step audit
rows are persisted as separate create-only gzip artifacts so the parent does
not retain roughly half a gigabyte of redundant JSON in memory; the analysis
keeps full-resolution output coordinates and verifies every compressed trace
hash.

## Asset protection contract

- Immutable: all R316/R336/R339 assets, R338 assets, the advisory package,
  existing claims/questions/verdicts, and the selected paper title.
- New R340 assets only: `memory/rounds/R340`,
  `results/r340_fresh_model_validation`, one R340 runner/probe, reusable pure
  seams if needed, and focused tests.
- Formal artifacts are create-only. Rehearsals cannot create a formal output.
- Once either formal phase begins, failure/interruption is retained and no
  retry, threshold repair, point replacement, waveform replacement, or model
  repair is authorized in R340. The validation seal cannot be prepared until
  the candidate artifact passes construction and its exact hash is verified.

## Cross-references

- `memory/questions/Q-0089.md`
- `memory/claims/CLM-0890.md`
- `memory/rounds/R339/verdict.md`
- `memory/rounds/R339/host_capacity.json`
- `paper/decoupling_marl_model_first/LINE.md`
- `docs/adr/0013-candidate-before-validation-and-capacity-bound-long-horizon.md`
