---
round: R333
state: aborted
opened: '2026-08-04'
closed: '2026-08-04'
supersedes_rounds: []
superseded_by_round: null
abort_reason: publication evidence audit found three unsealed material runtime dependencies
  and a reward-path contract conflict
superseded_note: null
---
# R333 plan - minimal physical PQ disturbance identification

## TL;DR

Answer Q-0085 with the smallest source-bound physical execution that can fail
quickly. At the two frozen HS0/HS1 operating points, execute one zero baseline
and one signed pair of 0.05-system-p.u. active-power perturbations on the
existing nonzero `PQ_Bus14` device. Pre-register absolute timed PQ events before
system setup at 0.5 s and 1.5 s, run zero M/D and zero ESD1 requests throughout,
and compare the delivered-output response with the immutable R316/R329 input
convention under the prospectively fixed
`d_node = -delta_P_load * e_bus14` map. Do not run a controller, distributed
runtime, training, reward, or EVAL.

## Authority and workload

- Direct question: `memory/questions/Q-0085.md`, opened by the valid R332 BLOCK.
- Scientific authority: the selected manuscript `LINE.md`, CLM-0870, the R332
  feed/results, immutable R316 dynamic model, immutable R329 package, installed
  ANDES 2.0.0 source, and versioned official ANDES sources.
- Workload: `evidence`, because the round creates new physical trajectories and
  may dispose Q-0085. The conference title remains byte-for-byte unchanged.
- Research Supervisor route: one bounded primary-source `research` note on the
  official runtime PQ update and event semantics; no landscape search.
- Ask Matt route: `diagnosing-bugs`. The tight red loop is the current
  `AndesModelFirstEnv` rejection of every nonempty PQ edit. The fix must add a
  new seam rather than mutate that sealed environment.

## Ranked engineering hypotheses

1. The legacy direct `Ppf.v` mutation is unsuitable for the formal bank; the
   official timed `Alter` path must be registered before `setup()` and must call
   the indexed model `set` method at the event.
2. A runtime write or callback without a registered critical time can repeat or
   drift under solver retries; absolute timed assignments should avoid this.
3. A correct event can appear delayed if the exact-event stored row is treated
   as post-event response; ANDES stores that row before the event callback, so
   the next stored point is the first post-event sample.
4. The physical PQ response may be valid but not equivalent to the frozen
   R329 control-input disturbance map; that is a scientific BLOCK, not an
   implementation bug.

## Methodology

Use red-first implementation checks, one bounded mechanical canary, and one
sealed six-record physical bank. Identification, equivalence, and exclusion
rules below are frozen before any trajectory access.

## Frozen physical bank

- Operating points:
  - `HS0`: per-device M/D `177.5/88.75`, tie R/X scale `1.10`, initial SOC `0.41`.
  - `HS1`: per-device M/D `202.5/101.25`, tie R/X scale `1.35`, initial SOC `0.51`.
- Disturbance device: existing `PQ_Bus14`, whose pre-perturbation active load is
  positive. Do not add devices or edit topology.
- Records: exactly six = two operating points times `zero`, `positive`, and
  `negative` active-power perturbations.
- Signed pair: `delta_P_load = +/-0.05` system p.u. on the 100-MVA system base;
  reactive power is unchanged. Positive means more consumption; negative means
  less consumption. Negative load or net-generation crossings are forbidden.
- Timing: pre-register absolute `Alter` assignments for `PQ.Ppf` and unchanged
  `PQ.Qpf` at 0.5 s, plus absolute restoration assignments at 1.5 s. The exact
  0.5-s and 1.5-s stored rows are pre-event; the next TDS stored points are the
  first post-event rows. The wrapper observes five 0.2-s disturbed periods and
  twenty 0.2-s recovery periods. Freeze five TDS subsegments per wrapper period
  and reject inherited `N_SUBSTEPS` overrides.
- Inputs throughout: zero M/D increments and zero ESD1 power request. The
  default Line_8 event remains disabled; G4 stays in service.
- Outputs: the same four physical 60-Hz frequency coordinates used by R316,
  plus raw frequencies, exact TDS grid, pre/write/readback/restored PQ values,
  M/D, zero requested/projected/internal/achieved ESD1 power, SOC, limiter and
  saturation telemetry, algebraic residuals, solver flags, Line_8/G4 status,
  and source/runtime identity.

## New implementation seam

- Preserve all R306-R332 source and result assets byte-for-byte, especially
  `model_first_env.py`, the R316 model, and the R329 package.
- Add one new model-first event subclass in a new module. Its pre-setup hook
  registers four absolute `Alter` events (active/reactive apply and restore),
  freezes both the PQ configuration and the already-constructed voltage
  conversion limiter, and wraps the official callback only to record exact
  before/after values and per-event fire counts. It validates exact device
  identity, finite target values, positive-load boundary, event inventory,
  model-set readback, and restoration. Do not expose a post-setup direct-write
  path as formal evidence.
- Add one pure R333 classifier under `probes/`, one thin prepare/execute/analyse
  adapter under `scripts/`, and focused tests. The physical command is WSL-only
  through `scripts/andes_scratch.py`; artifacts are create-only with sidecars.
- The temporary rejection harness is not evidence and must be deleted before
  round close.

## Prospective validity guards

Interpret no response metric unless all guards pass:

- exact round/question/seal/source/parent/runtime identity and deterministic
  analysis replay;
- installed ANDES version and pinned relevant PQ, model-set, TDS-event, and
  storage sources match;
- exactly six unique completed records, no missing or extra record;
- exact device, system base, active/reactive quantity, sign, event time, hold,
  restoration, and wrapper/TDS grid readbacks;
- the registered event inventory targets only `PQ.Ppf`/`PQ.Qpf`, uses absolute
  assignment, fires once at each frozen time, returns the expected readbacks,
  and restores the exact pre-event values;
- constant-power weights are exactly one for active/reactive constant-power
  terms and zero for current/impedance terms; both the PQ conversion setting
  and its constructed limiter are disabled; `PQ_Bus14.ue` stays active and no
  active `FLoad` or `ZIP` points to that exact PQ device;
- every record carries the sealed round hash and immutable R316 model hash;
  analysis regenerates the Bus14 node input, five-step hold, twenty-step
  recovery, frozen coordinate transform, and R316 prediction from verified
  parent assets and rejects any mismatch before reading response metrics;
- requested HS0/HS1 M/D, tie scaling, and SOC match the sealed point contract;
  actual `Line_4/5/6` R/X readbacks equal their frozen nominal values times the
  point scale; every stored M/D, SOC, and internal `Pext0/Pext/Pref/Psum` trace
  passes the zero-control readback guard;
- no M/D write, topology drift, Line_8 event, G4 outage, ESD1 request, command,
  achieved power beyond `1e-6` system p.u., limiter/recovery activation,
  external saturation, SOC boundary event, solver failure, non-finite state,
  excessive algebraic residual, or ambiguous negative-load crossing;
- both zero baselines have finite drift records and every signed response has
  observable signal above its matched baseline drift.

## Prospective identification and equivalence rules

- Physical channel identification passes only if the requested PQ delta and
  readback delta agree within `1e-12` system p.u., restoration agrees within
  `1e-12`, both signed responses have common-frequency peak signs opposite to
  load sign, and each signal-to-baseline-drift energy ratio is at least 10.
- Pair nonlinearity is the energy of the positive-plus-negative midpoint after
  matched-baseline subtraction divided by signed signal energy; require at most
  `0.10` at each operating point.
- Map the physical perturbation prospectively as
  `d_node = -delta_P_load * [0,0,1,0]` in the immutable R316/R329 node-input
  convention. Simulate the immutable R316 retained realization from zero state
  over the same five-step rectangular input and twenty-step recovery.
- At each signed record require reduced-versus-physical total NRMSE at most
  `0.15` and global-peak-normalized maximum vector residual at most `0.20`, the
  unchanged R316 finite-bank envelope. No refit, scale correction, time shift,
  sign flip, output selection, or outcome-driven threshold change is allowed.

## Prospective decision tree

- `INVALID-PHYSICAL-DISTURBANCE-IDENTIFICATION`: any identity, inventory,
  source, execution, restoration, zero-control, numerical, replay, or exclusion
  guard fails. Interpret no identification or equivalence metric.
- `BLOCK`: execution is valid but the independent physical channel is not
  observable with the registered sign/timing, paired nonlinearity exceeds the
  bound, or any registered equivalence metric fails.
- `QUALIFY`: all identification and equivalence rules pass. This validates only
  one Bus14 active-load channel, one amplitude/shape, two operating points, and
  the phasor-domain electromechanical platform. Because R329 admits an arbitrary
  four-node disturbance vector while this bank identifies one physical column,
  a separately sealed successor disturbance model remains mandatory before any
  physical closed loop.

`ALLOW` is intentionally unreachable in this minimal bank: one location and
one waveform cannot validate the complete R329 disturbance object. This is a
small-fast identification round, not a controller-authorization round.

## Verification and stopping conditions

- Run preflight before implementation. Write focused red tests first for the
  missing event module and for every detector rule that can change the verdict.
- Before sealing, run focused tests, lint, source-drift checks, a WSL canary on
  development-only temporary output, and preflight again. The canary may only
  confirm executable mechanics; it cannot tune the formal bank or thresholds.
- Seal before the six formal trajectories. Run the formal bank once, analyse
  twice deterministically, and never repair the contract after outcome access.
  Before the first trajectory, create a non-overwritable formal-attempt marker;
  any interruption leaves that marker and forbids an automatic retry.
- Complete independent evidence and power-system publication audits before
  claim registration. Then publish feed, claim, verdict, Q-0085 disposition,
  selected-line navigation, manifest entry, ledger validation, render,
  repository health, whitespace check, and the full test suite once.
- Stop after the disturbance-channel judgment. No deterministic controller,
  distributed agent, reward, training, EVAL, topology claim, stability claim,
  safety claim, or title-result claim is authorized in R333.

## Asset protection

- Preserve R306-R332 plans, seals, results, feeds, claims, questions, verdicts,
  all protected environments, installed ANDES, the R316 model, and the complete
  R329/R330 package byte-for-byte.
- New durable assets are limited to the R333 plan, one new helper module, one
  classifier, one adapter, focused tests, create-only seal/results, feed, claim,
  verdict, Q-0085 disposition, at most one justified follow-up question, result
  manifest entry, and selected-line navigation refresh.

## Cross-references

- `memory/questions/Q-0085.md`
- `memory/claims/CLM-0870.md`
- `paper/decoupling_marl_model_first/reports/R332.md`
- `results/r316_dynamic_reduction/dynamic_model.json`
- `memory/rounds/R329/disturbance_estimator_seal.json`
