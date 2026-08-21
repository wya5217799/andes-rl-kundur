---
round: R390
state: completed
manuscript_line: converter-vsg-pq-decoupling
opened: '2026-08-14'
closed: '2026-08-14'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R390 plan — exact-R389 equilibrium and reduced-spectrum gate

**Opened**: 2026-08-14
**Driver**: Determine whether R389's sampled no-action growth is already present as a numerically reproducible local growing direction in the unchanged ANDES reduced model, without advancing time or opening control work.
**Parent**: CLM-1090; Q-0108

## TL;DR

Build the exact R389 four-stock-REGF2 object twice, initialize it independently
at native tolerances `1e-4` and `1e-6`, and inspect the finite ANDES reduced
state matrix without calling `TDS.run()`. Recompute its spectrum independently,
bind retained/folded REGF2 and PLL states by exact names, and classify only
equilibrium validity, numerical reproducibility, and the presence or absence of
a mode with real part above `1e-7`. A positive-real result remains a scientific
STOP under the paper-facing EIG eligibility guard and cannot authorize control,
learning, or a physical-stability claim.

## Snapshot at plan-time (oracle as of 2026-08-14)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0108 [opened R390] Does the exact R389 four-REGF2 equilibrium contain a finite, numerically resolved positive-real mode in the ANDES reduced state matrix that reproduces across two independently initialized numerical arms without advancing simulation time?
- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0107 closed-negative @ R389, by CLM-1090 — Can four stock REGF2 VSM devices replace the four Kundur source models one-for-one and complete structurally clean native initialization plus a no-exogenous-action short trajectory without residual, convergence, finite-value, or electrical-guard failure?
- Q-0106 closed-negative @ R388, by CLM-1085 — Do one-device-at-a-time signed Pref and Qref steps on the structurally clean four-REGCV1 Kundur object produce correctly applied, signed, target-attributed active and reactive power responses without solver or electrical-guard failure?
- Q-0105 closed-positive @ R386, by CLM-1075 — Can the same four-device REGCV1 card pass native initialization and a zero-input short TDS when the unchanged packaged Kundur static tables are reconstructed with no legacy synchronous-machine, governor, or exciter records?

## Methodology

### Fixed scientific object

- ANDES 2.0.0 in the registered WSL environment.
- The packaged Kundur XLSX/JSON inputs and R389 static-only derivation, with
  exact source/derived hashes.
- Ten buses, fifteen lines, four static generators at buses 1--4, and exactly
  four stock REGF2 devices plus their four independently linked PLL2 objects.
- The R389 input card and deterministic post-setup runtime card, including
  `Sn=900`; no parameter, network, event, controller, setpoint, or action change.

### Two-arm equilibrium bank

Each arm builds a fresh system and runs setup, PFlow, and native TDS
initialization only. The ordered arms are:

1. `r389_reference_tol_1e-4` with `TDS.config.tol=1e-4`;
2. `sensitivity_tol_1e-6` with `TDS.config.tol=1e-6`.

No arm calls `TDS.run()`. Archive time and the complete x/y/z/f/g vectors
immediately before and after EIG calculation. Require bitwise-equal time and
exactly equal x/y/z vectors; the recorded maximum delta is recomputed from the
archived vectors and cannot substitute for them. Both arms are attempted exactly once and run
serially because launcher and coordination overhead dominate two short jobs.

### Equilibrium and matrix evidence

For every arm archive PFlow/init/test status; complete initialization residual
and clamp diagnostics; finite x/y/z/f/g and Jacobian status; exact inventory,
input/runtime cards, references, case/source hashes; `EIG.As`, `EIG.mu`,
`EIG.x_name`, zero-time-constant/folded-state indices, and removed/dead
algebraic indices. Require `As` square, all values finite, unique names, and
`len(x_name) == As.shape[0] == len(mu)`.

Archive the complete DAE x-name/address/Tf, algebraic-name, and discrete-name
catalogs, and require exact x/y/z/f/g vector lengths against those catalogs.
Also archive the exact EIG augmented algebraic catalog in fold order: original
DAE algebraic names followed by the zero-Tf state names. Validate every
removed/dead algebraic index against this augmented catalog, not against the
shorter original DAE algebraic catalog.
Resolve each registered REGF2/PLL dynamic variable by model address to
`dae.x_name`, then by one unique exact name in `EIG.x_name`; record every
retained, zero-Tf-folded, or nonzero-Tf constraint-eliminated state. Validate
all zero-Tf addresses/names and dead-algebraic indices against those catalogs.
Never use a raw DAE address as an eigenvector row after reduction.

Recompute the spectrum and left/right eigenvectors with SciPy from the captured
`As`. Reconcile the unordered spectra one-to-one using normalized complex
distance `abs(a-b)/(1+abs(a)) <= 1e-8`. Require normalized right-eigenpair
backward error no greater than `1e-8` and eigenvector condition number no
greater than the established project guard `1e12`. Separate near-zero modes
using the installed EIG tolerance `1e-6`; select the spectral-abscissa mode over
all other finite modes, not only an oscillatory frequency band.

Across the two arms require exact DAE/reduced-state catalog and matrix-dimension
identity, equal positive-real counts, and canonical leading-set normalized
distance no greater than `1e-4`. Conjugate partners collapse by absolute
imaginary part and tied spectral-abscissa modes are compared as unordered sets.
Archive and validate the actual post-setup/init TDS tolerance in each arm. The R389 sampled log-norm slope may
be compared with the leading real part only after classification as a
diagnostic consistency check; it is not a gate, eigenvalue estimate, or causal
proof. Full-precision state participation may be reported only as model-state
association and never as output observability, causal attribution, or a
physical stability certificate.

## Outcomes

- `ANALYSIS-INVALID`: source/provenance/schema/dimension/name/diagnostic capture,
  unexpected execution, or artifact-integrity defect.
- `STOP-REGF2-EQUILIBRIUM-INVALID`: complete evidence shows PFlow, native init,
  native test, residual, finite-value, or no-time/no-state-advance failure.
- `STOP-REGF2-SPECTRUM-NUMERICALLY-UNRESOLVED`: both equilibria are valid but
  independent/native spectra, eigenpair residual/conditioning, or cross-arm
  reproduction fails the frozen numerical guards.
- `STOP-REGF2-POSITIVE-REAL-GUARD`: both arms are valid and reproducible and at
  least one finite mode has `Re(lambda) > 1e-7`. This is a valid negative for
  paper-facing EIG eligibility and only a source-spectrum mechanism diagnostic.
- `REGF2-EIG-ELIGIBLE-NO-POSITIVE-REAL-MODE`: both arms are valid and
  reproducible and neither contains a mode above `1e-7`. This does not overturn
  R389 or prove stability; the trajectory-growth cause remains unresolved.

Exactly one formal bank is permitted. Any output-directory collision,
unexpected exception, missing evidence, or post-seal source change is invalid
and consumes no scientific interpretation. There is no automatic retry.

The sealed parent comparison is
`results/research_loop/r389_regf2_object_init_gate/formal_execution.json`.
Its sampled growth is used only after classification as the bounded diagnostic
consistency comparison described above, never as an EIG threshold or baseline
that can change an outcome.

## 资产保护契约

R389 attempt, execution, analysis, feed, claim, verdict, source manifest, and
seal remain immutable and are read/hash-only parents. The Kundur topology,
static operating point, REGF2/PLL object, device parameters, R389 trajectory,
and every controller/learning asset remain unchanged. R390 adds only a pure
classifier, a stable runner adapter, tests, one source seal, and one create-only
two-arm equilibrium/EIG evidence bank.

## Formal launch contract

- `formal_entry`: `scripts/run_r390_regf2_equilibrium_eig_gate.py`
- `rehearsal_command`: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r390_regf2_equilibrium_eig_gate.py rehearse`
- `rehearsal_scope`: setup-only construction, source/case/card/hash checks,
  dependency/API checks, output-collision checks, and elapsed/resource capture;
  no PFlow, TDS initialization, EIG calculation, or trajectory.
- `rehearsal_checks`: exact contract, the complete frozen R389
  seal/attempt/execution/analysis/manifest chain, source and parent hashes;
  installed ANDES, REGF1/REGF2/PLL/EIG/TDS/System/DAE sources, NumPy and SciPy
  identities and required runtime API surfaces; builder/inventory/card construction; no retired
  dynamic/event objects; source/hash determinism; create-only output absence;
  capacity and process telemetry.
- `capacity_evidence`: `memory/rounds/R390/capacity_evidence.json`, measured by the
  setup-only rehearsal and refreshed immediately before sealing.
- `host_process_budget`: 1 WSL Python formal process.
- `wsl_python_processes`: 1 total formal process; the two dependent arms execute
  serially inside it.
- `native_threads_per_process`: 1 for OpenMP, OpenBLAS, MKL, and NumExpr.
- `other_reserved_processes`: measured immediately before seal and required 0
  for this line's formal workers.
- `seal_command`: `/home/wya/andes_venv/bin/python scripts/run_r390_regf2_equilibrium_eig_gate.py prepare`
- `seal_path`: `memory/rounds/R390/formal_seal.json`.
- `formal_execute_command`: from a clean scratch launch directory, invoke
  `/home/wya/andes_venv/bin/python /mnt/c/Users/27443/Desktop/andes-rl-kundur/scripts/andes_scratch.py /mnt/c/Users/27443/Desktop/andes-rl-kundur/scripts/run_r390_regf2_equilibrium_eig_gate.py execute --expected-seal-sha256 <sha256>`.
- `formal_output`: create-only `results/research_loop/r390_regf2_equilibrium_eig_gate`.
- `completion`: one immutable execution record, analysis, and manifest covering
  both ordered arms and exactly one classifier result.
- `monitoring`: the two short dependent arms run serially; observe once near
  the rehearsal-derived ETA or on terminal artifact creation.
- `retry`: none automatically. A defect found before sealing may be repaired
  prospectively and then rehearsed and sealed once. Any post-seal defect,
  including one before formal-attempt creation, aborts R390 and requires a
  separately authorized successor; any formal-attempt defect closes R390
  invalid.

## Cross-references

- Q-0108
- CLM-1090
- `paper/converter_vsg_pq_decoupling/reports/R389.md`
- `paper/converter_vsg_pq_decoupling/working/R389_diagnosis.md`
- `paper/converter_vsg_pq_decoupling/working/route_contract.md#r390-mechanism-only-decision`
