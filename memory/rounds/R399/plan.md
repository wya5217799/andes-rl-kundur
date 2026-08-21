---
round: R399
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-15'
closed: '2026-08-15'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R399 plan — Yang-compatible M/D joint-headroom gate

**Opened**: 2026-08-15
**Driver**: Execute the new line's mandatory non-learning gate before any
MARL implementation or training.
**Parent**: CLM-1135; `paper/yang_md_decoupling_marl/working/route_contract.md`

## TL;DR

Workload: `evidence`.  Freeze fresh heterogeneous development/evaluation
banks, select one global deterministic local-neighbour M/D law on development
only, then measure an outcome-seeing finite-law oracle on evaluation.  PASS
requires at least five-percent evaluation improvement on both registered
physical decoupling endpoints with three-percent common-mode no-harm and all
action/failure guards.  No learning or training is authorized.

## Snapshot at plan-time (oracle as of 2026-08-15)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0111 closed-negative @ R397, by CLM-1130 — Do one-device-at-a-time signed Pref and Qref steps on the two-unit PPVSM1 diagnostic cell produce correctly applied, signed, target-attributed active and reactive power responses without solver or electrical-guard failure, thereby opening only a separately registered droop-slope matching verification?
- Q-0110 closed-positive @ R396, by CLM-1125 — Does the projected-passive dual-droop VSM (PPVSM1) two-unit diagnostic cell pass clean native initialization, a 0.2-second zero-input stationarity gate, and a spectrum guard with no positive-real mode and no neutral degeneracy beyond the network common-angle reference, thereby opening only a separately registered signed P/Q authority gate?
- Q-0109 closed-positive @ R392, by CLM-1105 — Which installed REGF2 feedback path or parameter carries the two reproducible positive-real local modes of the exact R391 four-REGF2 equilibrium, under prospectively frozen one-variable-at-a-time parameter-perturbation EIG arms?

## Methodology

### Mission boundary

- Outcome: close R399 with one `HEADROOM-PASS`, `STOP-NO-JOINT-HEADROOM`, or
  `ANALYSIS-INVALID` result and a bounded claim.
- Current authority: `yang-md-decoupling-marl` is active at
  `registered-awaiting-nonlearning-joint-headroom`; no other round is active.
- Permitted: one pure analysis module, one formal WSL runner, focused tests,
  rehearsal/capacity/seal, fresh non-learning physical traces, result/feed/
  claim/verdict/navigation closure.
- Forbidden: learner code, training, architecture replacement, old numerical
  evidence transfer, old-line writes, topology or VSG-count claims.
- Terminal: R399 is closed after the registered G1 classification.  PASS may
  make a later G2 round eligible but cannot launch it here.

### Scientific object and comparator identifiability

- Same modified Kundur connectivity, four VSG proxies, actor row order, direct
  normalized `delta_M_i,delta_D_i`, decoder, box `[-1,1]`, slew `0.25`, update
  interval `0.2 s`, initialization, post-processing, and local-neighbour
  observations for all arms.
- Arms: zero action and the nine existing `km in {0.5,1,2}` by
  `kd in {0.5,1,2}` local-neighbour laws.  Historical code is revalidated;
  no historical trace or value enters the bank.
- Development chooses one global deterministic law.  Evaluation uses that law
  as the deployable baseline and a non-deployable outcome-seeing oracle that
  may select one of the same nine laws per heterogeneity profile.
- Identified estimand: finite-bank physical joint headroom beyond the selected
  deterministic implementation.  The only privileged difference is the
  oracle's post-outcome profile selection.
- Allowed positive consequence: authorize a later learning canary as a
  training-necessity hypothesis.  Stay out of deployability, learner value,
  coordination, general algorithm superiority, topology generalization,
  stability certification, EMT, HIL, and field claims.
- Comparison-identifiability return: `ALLOW` for this bounded headroom
  estimand; oracle privilege is explicit and cannot be promoted into a
  controller claim.

### Frozen coordinates, estimators, and windows

- Physical frequency uses the installed ANDES `60 Hz` base.  The controller
  adapter alone converts the protected legacy `50 Hz` observation slots.
- `z_c(t)=mean_i(f_i(t)-60)`.
- `T_d` rows are `[1/2,1/2,-1/2,-1/2]`,
  `[1/sqrt(2),-1/sqrt(2),0,0]`, and
  `[0,0,1/sqrt(2),-1/sqrt(2)]`; `z_d=T_d(f-60)`.  These are arithmetic endpoint
  coordinates, not eigenmodes.
- Every signed pair uses the odd response
  `z_odd=(z_positive-z_negative)/2`, preventing pre-event offsets and even
  nonlinear terms from becoming the signed response.
- Off-diagonal cross-response energy per profile is the full `30 x 0.2 s`
  sum of mean-square `z_d,odd` under the common pair plus square
  `z_c,odd` under the differential pair, normalized by squared registered
  probe magnitude.
- Disturbance differential energy is the sum of mean-square `z_d,odd` for the
  common, differential, and localized signed pairs, each normalized by its
  squared registered magnitude, over the same six-second window.
- Common guard endpoints are common-frequency absolute integral, worst-unit
  absolute peak deviation, and worst finite-difference RoCoF including the
  recorded pre-step initial frequency.  Differential settling is reported as
  the first time after which the differential norm remains below two percent
  of its pair peak; it does not decide G1.
- Action endpoints are RMS normalized effort, boundary-aware total variation,
  maximum within-step row dispersion, saturation fraction, bounds, slew, and
  literal M/D decoder/readback identity.
- Unit of analysis is one heterogeneity profile containing all three signed
  pairs.  Aggregate ratios use sums across profiles.  Uncertainty is the four
  evaluation-profile table plus the leave-one-profile-out aggregate range;
  it is descriptive finite-bank sensitivity, not population inference.

### Fresh heterogeneous banks

All values below are fixed before candidate execution.  Baseline M/D values
remain inside the paper action box.  Steady Bus14/Bus15 active loads change
operating point and spatial distribution while connectivity stays fixed.

| split/profile | baseline M | baseline D | steady `(Bus14,Bus15)` | common/differential magnitude | localized pair |
|---|---|---|---|---|---|
| development/dev-a | `(160,240,180,220)` | `(70,130,90,110)` | `(2.28,0.20)` | `0.8` | `PQ_0`, `0.9` |
| development/dev-b | `(220,180,240,160)` | `(110,90,130,70)` | `(2.08,0.60)` | `1.0` | `PQ_Bus14`, `1.1` |
| evaluation/eval-a | `(150,250,190,210)` | `(60,140,80,120)` | `(2.48,0.30)` | `0.9` | `PQ_1`, `1.0` |
| evaluation/eval-b | `(250,150,210,190)` | `(140,60,120,80)` | `(2.18,0.10)` | `0.7` | `PQ_Bus15`, `0.8` |
| evaluation/eval-c | `(170,230,250,150)` | `(75,125,145,55)` | `(1.88,0.60)` | `1.1` | `PQ_0`, `1.2` |
| evaluation/eval-d | `(230,170,150,250)` | `(125,75,55,145)` | `(2.38,0.30)` | `0.8` | `PQ_Bus14`, `0.9` |

Each profile has exactly six scenarios: common positive/negative distributes
one quarter of the signed magnitude to each of `PQ_0`, `PQ_1`, `PQ_Bus14`,
`PQ_Bus15`; differential positive/negative applies plus one quarter at the
two area-1 locations and minus one quarter at the two area-2 locations (then
flips sign); localized positive/negative applies the registered magnitude at
the registered location.  Seed is `399`; random disturbance, communication
failure/delay, and the installed Kundur toggler are disabled.

### Selection and decision tree

1. A row is invalid on incomplete steps, TDS failure, nonfinite endpoint,
   identity mismatch, action bound/slew violation, or unregistered key.
2. On development, an arm is eligible only when every profile is valid,
   saturation is at most `5%`, and common integral, worst peak, and RoCoF are
   each no worse than `103%` of zero.  Select one global arm by minimum worst
   of its two aggregate ratios to zero; tie by ratio sum, action RMS, then arm
   id.  Zero is not an eligible deterministic candidate.
3. On each evaluation profile, an oracle candidate is eligible only when all
   validity/action guards pass; common integral, worst peak, and RoCoF are each
   no worse than `103%` of the selected deterministic law; action RMS and total
   variation are each no worse than `110%` of that law; and saturation is at
   most `5%`.  Select by minimum worst of the two physical ratios to that law,
   with the same tie order.
4. `HEADROOM-PASS` requires aggregate oracle improvement at least `5%` on both
   off-diagonal and disturbance differential energy; every selected profile
   satisfies the three-percent common guards and ten-percent stress guards;
   every selected trace has total variation above `1e-6` and row dispersion
   above `1e-6`; all formal completion, identity, bound, slew, saturation, and
   provenance checks pass.
5. A complete valid bank not meeting every PASS item returns
   `STOP-NO-JOINT-HEADROOM`.  Missing/duplicate rows, failed provenance,
   malformed seal, any invalid physical row, or no eligible deterministic/
   oracle law returns `ANALYSIS-INVALID`.  Neither stop nor invalid permits
   training in this round.

### Design red-team return

- Highest risk: outcome selection could masquerade as deployment.  Repair:
  profile-conditional oracle is labelled non-deployable everywhere and only
  supports training necessity.
- Leakage risk: tuning on evaluation.  Repair: all nine arms and development
  selector are frozen; deterministic selection reads development only;
  evaluation is opened only after seal and cannot alter metrics or thresholds.
- Metric-label risk: coordinate scores could replace physics.  Repair: signed
  input-output energies use physical 60-Hz traces and common/peak/RoCoF/action
  guards; reward is absent.
- Comparator risk: oracle receives more action or information.  Repair: same
  executed family, action box, slew, timing, controller inputs, and simulation
  count; only post-outcome profile selection differs.
- Pseudoreplication risk: six scenarios per profile are not six independent
  populations.  Repair: profile is the analysis unit; sensitivity is
  finite-bank leave-one-profile-out, with no population p-value.
- Alternative explanation: gains may be purchased by action stress.  Repair:
  prospective RMS/variation, saturation, bound, and slew guards.
- Vulnerability decision: no blocking item remains before implementation;
  formal result still requires Result and Claim challenge on the canonical
  feed.

### Ask Matt engineering handoff and TDD seams

- Scientific acceptance: the decision tree above classifies one complete
  sealed bank without inspecting reward or training outputs.
- Authorized writes: one reusable pure module under `src/andes_rl_kundur/
  evaluation`, one `scripts/run_r399_*` adapter, focused public-seam tests,
  and R399 operational/result assets.
- Public seam 1: `build_contract()` returns the exact closed JSON contract.
- Public seam 2: `summarise_profile(records, contract)` converts six signed
  physical records into endpoint and guard summaries.
- Public seam 3: `classify_bank(summaries, contract)` enforces split isolation,
  deterministic selection, oracle selection, PASS/STOP/INVALID, and no
  training.
- Public seam 4: runner `rehearse`, `measure-capacity`, `prepare`, and
  create-only `execute` bind source/runtime/seal/output provenance.
- Verification: red-green slices at these seams, related V4/object/action
  regressions, formal rehearsal/capacity/seal, second preflight, terminal
  hashes/manifest, then repository close gates.

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r399_md_decoupling_headroom.py execute --expected-seal-sha256 <sha256>`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r399_md_decoupling_headroom.py rehearse`
- rehearsal_scope: same-pre-attempt-path; source/parent hashes, installed
  package/case, active line/plan, closed contract, output absence, no trajectory
  and no attempt.
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence, active_plan, active_line, contract_closed, physical_trajectory_executed=false
- capacity_evidence: memory/rounds/R399/capacity_evidence_v3.json
  Representative full-length zero-action jobs use worker rungs `1,2,4`; select the highest
  all-valid rung with at least five-percent throughput gain over the preceding
  accepted rung and projected worker RSS below half the measured WSL available
  memory.  Capacity traces are excluded from evidence.
- host_process_budget: 5
  Maximum pre-seal candidate including launcher;
  replace with measured selected workers plus launcher before final preflight.
- wsl_python_processes: 5
  Maximum pre-seal candidate including launcher and
  four process-pool workers; replace with measured selection before seal.
- native_threads_per_process: 1
  Applied to launcher and every worker.
- other_reserved_processes: 0
  Rechecked before capacity, seal, and execute.
- Formal jobs: `6 profiles x 6 scenarios x 10 arms = 360` complete records;
  development and evaluation are both executed after one immutable seal, but
  classifier code enforces development-only deterministic selection.
- Formal outputs are create-only under
  `results/research_loop/r399_md_decoupling_headroom/`; no retry is authorized.

### Pre-seal operational correction

- The first completed capacity ladder is preserved at
  `capacity_evidence.json`; it measured all three registered rungs and selected
  four workers, but omitted the preflight alias
  `whole_host_python_process_budget` while already recording the identical
  value as `host_process_budget` and `wsl_python_processes`.
- Before any seal or formal attempt, the runner/test seam was extended to
  create `capacity_evidence_v2.json` from the hashed v1 record.  V2 adds only
  that schema alias plus explicit supersession/current-source provenance;
  measured rungs, resources, selection, ETA, and scientific contract remain
  unchanged, and `physical_capacity_rerun_executed=false`.
- Preserve the original rehearsal and capacity files.  A new no-trajectory
  rehearsal binds the corrected runner before each derived record and sealing.
- The deterministic preflight then required an `empirical_anchor` that counts
  the launcher as well as the four simulator workers.  Preserve V2 and derive
  `capacity_evidence_v3.json`; V3 adds that anchor, cites the already measured
  accepted four-worker rung, and still records no physical rerun.  No seal or
  formal attempt existed during either schema correction.

## Gate

- `HEADROOM-PASS`: all registered joint-benefit, no-harm, action, validity, and
  provenance gates pass; authorizes only a separately registered G2 canary.
- `STOP-NO-JOINT-HEADROOM`: complete valid finite bank lacks the registered
  joint increment or guard; line stops before learning.
- `ANALYSIS-INVALID`: bank/provenance/identity/completion contract fails; no
  positive or negative scientific conclusion, no same-round retry.

## 资产保护契约

- Preserve every existing dirty-worktree asset; do not clean, reset, overwrite,
  or reformat unrelated files.
- Do not edit V4/base environment, old feeds/claims/results/checkpoints, other
  manuscript lines, route thresholds, title wording, or training assets.
- Add only R399 plan/operational artifacts, the bounded pure module/runner/
  tests, fresh R399 result root, one line feed/claim/verdict, and required
  navigation/manifest pointers.
- Formal and capacity outputs are create-only; a post-seal pre-attempt failure
  aborts R399 and needs a successor round.

## Cross-references

- CLM-1135/R398: new-line object, title semantics, gate order, five-percent
  joint floor, three-percent common no-harm, and no-training boundary.
- CLM-0990/R369: old fixed development bank stopped only its formulation;
  values and traces are excluded here.
- CLM-0975/R365: historical interface code is reusable only after fresh source,
  identity, and physical readback verification.
