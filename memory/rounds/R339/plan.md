---
round: R339
state: completed
manuscript_line: decoupling-marl-model-first
opened: '2026-08-04'
closed: '2026-08-04'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R339 plan - full-DAE input-bridge diagnosis before any new holdout

**Opened**: 2026-08-04
**Driver**: Resolve Q-0087 by replacing the empirically assumed static load-to-
control map with separately derived control and physical-load derivatives from
the installed ANDES DAE, while keeping every controller and fresh nonlinear
holdout out of scope.
**Question**: Q-0087
**Parent**: CLM-0885, the valid R336 negative physical-package result.

## TL;DR

Workload: `evidence`. The external resolution package is admissible as a
development diagnostic, not as evidence: it searched orders 8--14 on both
previously exposed points and its reproduction script depends on an absent
source bundle. R339 therefore freezes order 12 only as a candidate, rebuilds
the input bridge from the installed full DAE, fixes the post-step sampling
convention and coordinate weights before execution, and evaluates only against
the already exposed R336 records. Passing R339 may authorize one separately
sealed fresh model-validation round. It cannot authorize a controller,
distributed runtime, agent, training, EVAL, or title-result claim.

## Snapshot at plan-time (oracle as of 2026-08-04)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Kept as the immutable plan-time snapshot. -->

## Authority and source status

- Selected line: `paper/decoupling_marl_model_first`.
- Direct question: `memory/questions/Q-0087.md`.
- Parent evidence: `memory/claims/CLM-0885.md`,
  `results/r336_disturbance_package`, and the immutable R316 order-10 control
  model. R316 and R336 remain byte-for-byte unchanged.
- Advisory package:
  `C:/Users/27443/Downloads/input_bridge_resolution_package.zip`, SHA-256
  `fbe43205abc8f9f03ba1dff327f281b54322cc49fba08b8f0176f52e307afe41`.
  The user-provided extracted copy at
  `C:/Users/27443/Downloads/input_bridge_resolution_package/input_bridge_resolution_package`
  contains the same fifteen delivered files; it does not add the source bundle
  required by the hard-coded reproduction script.
  Its HS0 and HS1 outputs, the searched orders, empirical modes, and saved
  twelve-state files are development-only inputs. They are not imported as
  formal models and do not retain a holdout label.
- The package supports a bounded hypothesis: the current static input bridge
  is inadequate for the tested input-output behavior and a joint input-aware
  realization is worth testing. It does not yet prove that the static mapping
  is physically false, that twelve is a minimal physical order, or that the
  reported empirical poles are plant modes.

## Open Questions

- Q-0087: Which location-dependent input dynamics explain the upstream-load
  mismatch before any bridge repair?

## Methodology

### Gate 0 - repository-native admissibility

Record the advisory ZIP hash, inventory, external-path dependency, candidate
matrix dimensions, finite-value checks, spectral radii, and reported metrics.
Recompute any decision-bearing number from authoritative R316/R336 artifacts
or the new installed-DAE extraction; no package CSV or NPZ is authoritative.

### Gate 1 - exact descriptor and input derivatives

At the already exposed HS0 and HS1 operating points, rebuild the unchanged
model-first plant with original G4 and Line_8 in service, no M/D writes, zero
ESD1 request, no stochastic disturbance, and the R336 four-PQ baselines.
After equilibrium, persist:

- raw `Tf`, `f_x`, `f_y`, `g_x`, `g_y`, state/algebraic names and device
  ownership;
- the nonzero-time-constant differential block and the augmented algebraic
  block obtained by folding every zero-`Tf` state into the algebraic system;
- four independent ESD1 `Pext0` derivatives and four independent physical PQ
  `Ppf` derivatives, never `B_d=B_u M` or `D_d=D_u M`;
- the reduced continuous matrices, the four controlled-frequency output map,
  algebraic condition diagnostics, and exact source hashes.

Execute sixteen isolated per-channel jobs concurrently: two points, two input
families, and four physical channels. The parent Python process executes one
job while exactly fifteen spawned Python workers execute the other jobs, so
the whole-host total is sixteen, one process per measured physical core. Each
job constructs and closes its own ANDES system. All eight jobs for one point
must return bit-identical equilibrium vectors, raw Jacobians, catalogs,
operating-point readbacks, and source identity before their input derivatives
are combined. This split performs distinct derivative work; it does not add
replicate trajectories or change the scientific sample count.

Use central differences at the prospectively fixed absolute system-p.u. steps
`1e-4`, `1e-5`, and `1e-6`. At fixed equilibrium `x,y`, restore every input
and residual after each signed evaluation. A column is converged only when the
relative Frobenius differences between successive derivatives are each at
most `1e-5`, using denominator `max(||J||_F,1e-12)`, and the signed midpoint
residual ratio is at most `1e-6`. Limiter/recovery flags must remain on the
same branch for every signed evaluation.

The folded Schur state matrix must match the installed ANDES EIG reduction on
the same retained state catalog within relative Frobenius error `1e-8` and
maximum absolute error `1e-9`. Any zero-state, dead-algebraic, or state-
constraint handling that prevents an exact named-state reconciliation blocks
the round; it is not bypassed with a pseudoinverse. The augmented algebraic
block must have reciprocal 2-norm condition at least `1e-12`.

### Gate 2 - explicit sampled-time convention

Discretize the reduced continuous model at `0.2 s` under a zero-order hold.
R336 records the response at the end of each held interval, so the frozen
prediction convention is

`x[k+1] = A_d x[k] + B_d u[k]`,

`y[k] = C A_d x[k] + (C B_d + D_c) u[k]`.

The ordinary pre-step output convention is retained only as a diagnostic and
cannot be selected after seeing errors. Exact zero input must produce exact
zero output, channel units are system-base p.u. power, positive ESD1 input is
network injection, and positive PQ input is increased consumption.

### Gate 3 - mechanism discrimination on exposed records

Build full-order control and load Markov tensors for 25 samples. Compare three
prospectively named alternatives on the already exposed R336 records:

1. the old static mapped bridge;
2. the full DAE with separate control/load input derivatives;
3. one joint input-aware order-12 ERA candidate derived only from the full-
   order Markov tensor, never from a nonlinear trajectory fit.

The ERA contract is fixed at order 12, eight block rows, eight block columns,
25 Markov samples, no pole projection, and zero initial state. Before the
Hankel SVD, input coordinates are normalized by physical node-injection
energy: the common and three edge columns use the inverse Euclidean norm of
their frozen node basis, while each physical load column has unit norm. Output
coordinates use the frozen inertia-weighted transform; all four row norms
must be equal at each homogeneous operating point, otherwise the round blocks
rather than choosing an outcome-dependent output weight.

Full-DAE versus nonlinear R336 records uses the unchanged R336 limits: total
NRMSE at most `0.15` and peak-normalized vector residual at most `0.20` for
every signed impulse and triangle record. Full-order versus order-12 uses the
line-level predictor ceiling: NRMSE and peak-normalized residual each at most
`0.10` for every control and load channel over the same 25-sample horizon.
Empirical `0.50--0.62 Hz` and `0.72--0.86 Hz` bands are reported only for
attribution; no model order, scaling, state, or gate may be selected from them.

## Pre-registered outcomes and stopping rule

- `INVALID`: any source, equilibrium, catalog, unit/sign, restoration,
  finite-value, branch, rehearsal, or deterministic-replay guard fails.
- `BLOCK-DESCRIPTOR`: the folded descriptor cannot reproduce the named ANDES
  state reduction or the three finite-difference scales do not converge.
- `BLOCK-LINEARIZATION`: the descriptor is valid but the full separate-input
  model fails any exposed R336 nonlinear-response limit.
- `QUALIFY-MECHANISM`: the full separate-input model passes and the old static
  bridge fails, but the frozen order-12 candidate fails an internal reduction
  limit. This diagnoses the old bridge without selecting a reduced repair.
- `ALLOW-CANDIDATE`: descriptor, separate-input full model, and the frozen
  order-12 internal reduction all pass. This authorizes only a new atomic
  question and separately sealed fresh nonlinear holdout; it is not model-
  validation evidence by itself.

Stop after one of these outcomes. R339 creates no new nonlinear disturbance
trajectory, controller, closed loop, distributed runtime, reward design,
agent, training, EVAL, topology change, stability/safety claim, or manuscript
result.

## Formal launch contract

- formal_entry: python scripts/andes_scratch.py scripts/run_r339_input_bridge_diagnosis.py execute --expected-sha256 <seal>
- rehearsal_command: python scripts/andes_scratch.py scripts/run_r339_input_bridge_diagnosis.py rehearse --expected-sha256 <seal>
- rehearsal_scope: same-pre-attempt-path; no formal-attempt marker or result output
- rehearsal_checks: source_hash,parent_hash,installed_package,installed_case,output_absence
- wsl_python_processes: 16
- native_threads_per_process: 1
- capacity_evidence: memory/rounds/R339/host_capacity.json
- host_process_budget: 16
- other_reserved_processes: 0

The whole-host budget is a measured snapshot, not a repository constant. No
other line is executing, so R339 uses all sixteen physical cores: one parent
job plus fifteen isolated child jobs, each with one native numerical thread.
The sixteen-way rehearsal must succeed before this capacity value becomes
formal launch authority. A later round must capture a new snapshot and may
choose a different budget from the then-current machine evidence.

## Asset protection contract

- Immutable: every R316/R336 artifact, R338 file and output, advisory ZIP, and
  all existing claims and thresholds.
- New R339 assets only: `memory/rounds/R339`, `results/r339_input_bridge_*`,
  one R339 runner, reusable pure descriptor/reduction seams, and focused tests.
- Formal outputs are create-only. Rehearsal must traverse the same installed-
  runtime and source-closure checks without creating an attempt marker.
- If the formal attempt begins, interruption or failure is retained and no
  retry or threshold/model-order repair is allowed in R339.

## Cross-references

- `memory/rounds/R339/package_admissibility.md`
- `memory/questions/Q-0087.md`
- `memory/claims/CLM-0885.md`
- `paper/decoupling_marl_model_first/reports/R336.md`
- `paper/decoupling_marl_model_first/working/model_contract.md`
- `results/r316_dynamic_reduction/dynamic_model.json`
- `results/r336_disturbance_package/analysis.json`
