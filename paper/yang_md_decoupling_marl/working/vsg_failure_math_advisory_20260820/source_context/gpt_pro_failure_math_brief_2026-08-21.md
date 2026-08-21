# GPT Pro failure-mathematics brief — yang-md-decoupling-marl (2026-08-21)

**Manuscript line**: `yang-md-decoupling-marl` — "Decoupling-Oriented
Coordination of Paralleled VSGs With Multi-Agent Reinforcement Learning"
(ICEMS 2026, camera-ready 2026-09-07).
**Purpose**: after 44 closed evidence rounds (R398–R441), the experiment
program is execution-complete. This brief extracts the failure mechanisms
that remain mathematically unresolved, split into three tiers: (P)
problems solvable within the paper-writing window and worth entering the
manuscript; (M) mechanism science for the "why did it fail" ledger and the
journal extension; (C) a paper-grade proposition program. Every number
cited below lives in the sealed feeds/results shipped with this package;
nothing here is invented.

## 0. Fixed context (do not re-derive)

- **Object A (direct M/D)**: four VSG proxies, each actor writes its own
  bounded row $a_i=[a_i^M,a_i^D]\in[-1,1]^2$, asymmetric decoder
  $600a$ ($a\ge0$) / $200a$ ($a<0$), lower bounds $M_i\ge20$, $D_i\ge10$,
  slew limit 0.25 per 0.2 s update, 6-s post-disturbance windows, ANDES
  2.0.0 60 Hz phasor DAE, modified Kundur two-area.
- **Object B (energy port)**: feasibility-native ring-edge zero-sum power
  commands; frozen 0.4 Hz bandpass, $\zeta=0.35$, gain $K=3.5$ (dev-selected).
- **Endpoints**: off-diagonal response energy (signed probe pairs,
  common→differential and differential→common) and disturbance-driven
  differential energy; both lower-is-better. **Guards**: common-mode
  no-harm (frequency IAE / worst peak / RoCoF ≤ 1.03× deterministic
  reference) and action-stress no-harm (action RMS / total variation
  ≤ 1.10×), plus validity (TDS completion, slew legality).
- **Canary decision rule**: a learner passes only if it improves both
  endpoints (seed-median) AND passes every guard on every profile–seed block.
- **Prior GPT Pro answers already ingested** (do not duplicate; extend only):
  1. A1/A2 brief 2026-08-17 (channel placement, objective-to-gate gap) →
     `working/gpt_pro_md_decoupling_a1_a2_answer_2026-08-17.md` (registered).
  2. 8-question brief 2026-08-19 (R428–R432: value-scale divergence, slew
     invariant sets, dual-residual identity, message mechanism M1,
     penalty-modal analysis M2, Pareto framework M3, exact decoupling
     condition P1, bounded-SAC conditions P2) →
     `working/gpt_pro_power_marl_answer_2026-08-19.md`.
  3. Theory audit Tasks A–E (reduced-model separation iff homogeneous M,D;
     first-order multiplicative-authority lemma; index-1 DAE Schur channel;
     nonsmooth $O(\varepsilon^2)$ bound; no product lower bound) →
     `working/theory_audit_bundle/IMPORT_NOTE.md` (CONDITIONAL PASS).
  4. R402 canary causal audit → `working/r402_causal_validation_final_bundle/IMPORT_NOTE.md`.

## Tier P — paper-window problems (solve → may enter the manuscript before 2026-09-07)

### P1. Mechanism of the relaxed-plant failure block (R415/R437)
**Fact.** The frozen bandpass $K=3.5$ passes all guards on the stiff-plant
block (inertia ×1.15, damping ×0.85) and the new-conditions block, but
fails the differential ceiling on the relaxed-plant block (inertia ×0.85,
damping ×1.15): $r_d=0.9712>0.95$, all guards passing (CLM-1230). A second
disclosed gain $K=4.0$ fails the same block at $r_d=0.9506$ (CLM-1240).
**Refuted hypothesis.** R437 spectral diagnosis: the relaxed block's
differential spectrum keeps its dominant peak inside the 0.3–0.5 Hz
channel window (0.449 Hz, 58.7% window energy — above the passing blocks'
50.3–52.9%), so "the dominant mode leaves the 0.4 Hz channel" is REFUTED
(CLM-1340). The failure mechanism is therefore NOT located.
**Question.** Given the frozen reduced swing-type model of the four-VSG
two-area system (ANDES DAE, Object B), derive which closed-loop quantity
explains $r_d$ degrading by ~3–4% when $M$ is scaled ×0.85 and $D$ ×1.15
while the dominant mode stays at 0.449 Hz. Candidate mechanisms to test
against the data: (a) gain margin / sensitivity peak at the shifted mode;
(b) disturbance-to-differential closed-loop gain scaling with
$\sqrt{M}$-type scaling of the plant; (c) bandpass phase interaction with
the changed damping ratio; (d) settling structure of the 50-step window
(0.2 s updates, 10 s horizon). Deliver: a small-signal sensitivity formula
in the plant parameters whose sign and rough magnitude match
$r_d$: 0.938 (nominal) → 0.9712 (relaxed) → 0.9080 (stiff), plus the
specific observable that would confirm it (e.g. a frequency-dependent
sensitivity curve value at 0.449 Hz).
**Data.** `reports/R415.md`, `reports/R437.md`,
`results/research_loop/r437_relaxed_spectral/formal_analysis.json`,
`results/research_loop/r415_energy_port_extra_banks/formal_analysis.json`,
`results/research_loop/r415_energy_port_extra_banks/a4_md_relaxed/records.json`
(sealed 50-step traces, 10 records × 3 arms), bandpass definition
`results/research_loop/r408_v2_solving_gate/formal_analysis.json`,
unseen-gate baselines `results/research_loop/r409_heldout_gate/formal_analysis.json`.

### P2. Controller-delay boundary of the constructive result (R440)
**Fact.** On the frozen energy-port object, the bandpass $K=3.5$ passes
7/7 EIG-sound N-2 outage variants but fails the $r_d\le0.95$ ceiling under
controller-output delay: 1 step (0.2 s) → $r_d=0.950279$ (+0.03% over);
2 steps (0.4 s) → $r_d=0.989327$; $r_{\rm cross}$ stays comfortable
(0.606, 0.641), all guards passing (CLM-1350).
**Question.** The controller updates every 0.2 s, so a one-step delay is
one full update period. Derive the discrete-time (ZOH-sampled) closed-loop
phase/loss at the 0.4 Hz channel: why does one extra sample of delay move
$r_d$ from ~0.938 to ~0.950 and two samples to ~0.989? A simple
second-order bandpass + plant phase-slope argument should reproduce this
sensitivity; state the exact loop gain / phase-margin formula that predicts
the $r_d$ degradation slope, so the manuscript can quote an analytic delay
boundary instead of a measured one.
**Data.** `reports/R440.md`,
`results/research_loop/r440_robustness_expansion/formal_analysis.json`,
`results/research_loop/r440_robustness_expansion/delay/` (2 JSONs).

### P3. DAE first-order authority of multiplicative M/D feedback (Lemma 1 completion)
**Fact.** Manuscript §3.4 proves Lemma 1 (zero-bias multiplicative
parameter feedback has no policy-slope first-order Jacobian authority in
the ODE reduction) and records the index-1 DAE extension
$B_{u,r}=f_u-f_yg_y^{-1}g_u$ as an *unresolved boundary*: the actual ANDES
DAE Jacobians "have not been identified" (theory_audit_bundle
IMPORT_NOTE: "the theory can be strengthened only after obtaining the
actual reduced or DAE Jacobians").
**Question.** For the project plant (four VSG proxies on the modified
Kundur system, Object A), is $B_{u,r}$ nonzero? I.e., does the algebraic
(power-balance) coupling give multiplicative M/D feedback a first-order
local authority channel that the ODE lemma misses? Deliver: (a) the
symbolic index-1 reduction steps needed for this plant class (swing-type
buses with algebraic power flow), stating exactly which entries of
$f_y,g_y,g_u,f_u$ can make $B_{u,r}\ne0$; (b) a finite-difference recipe on
the ANDES equilibrium (perturb $u$, re-solve algebraic constraints, read
off the effective linear channel) that the project can execute to measure
whether the channel is active at the registered operating point; (c) the
paper-grade phrasing of a strengthened Lemma 1 conditional on that
measurement. If solvable: this converts a limitation paragraph into a
contribution.

**Related sub-question (reduced-model identifiability).** R405 measured
that static homogenization (the Proposition-1 condition implemented as
constant $M,D$) fails the physical gate in the nonlinear DAE, and the
route history includes attempts to recover the $4\times4$ reduced
Laplacian from measured trajectories. State what identifiable structure
($M$, $D$, $L$ up to what gauge and symmetry/balance residual) can be
legitimately recovered from the frozen signed-probe records, and what
residual bound would decide whether Proposition 1's exact-Laplacian
premise holds or fails in the actual plant — this determines whether the
reduced-model theorems apply to the measured system at all (the
manuscript's §3.3 currently refuses to insert a recovered coupling matrix
into Proposition 1).
**Data.** `manuscript/manuscript.md` (§3.4),
`working/theory_audit_bundle/IMPORT_NOTE.md`,
`src/andes_rl_kundur/env/andes/base_env.py`,
`src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py`,
`src/andes_rl_kundur/env/andes/v4_config.py`,
`src/andes_rl_kundur/evaluation/fast_md_authority.py`,
`reports/R399.md` (object definition).

## Tier M — mechanism science ("why did it fail", journal extension)

### M1. Why the sign-corrected constrained dual saturates at its ceiling and never closes (R424–R427)
**Fact.** Guard-aligned action constraints (executed-action squared energy
+ absolute step-to-step change, per-episode projected multiplier, step
0.05, ceiling 10.0) entered with a reward sign in R424 (defect, verified:
gradient inner product −97.6; dual self-reinforced to ceiling; bang-bang
collapse). Sign-corrected R425: action-stress guards move 36→12 failed
blocks, RMS residuals collapse 38.3–90.8× → 1.1–10.1×, but **every
multiplier still sits at the 10.0 ceiling in 6/6 runs** and no arm passes
all guards. R427 (PopArt-style critic target normalization, differential
channel) suppresses the critic divergence (original-scale Q4/Q1 0.32–1.75
vs 4.65–6.29) and stops the action-stress guard failures across all 36 CD
blocks, while the dual STAYS ceiling-capped and the residual becomes
frequency restoration (common-frequency + worst-peak no-harm fail in every
block).
**Question.** Model the projected dual ascent with fixed step 0.05 and
ceiling 10.0 on this nonconvex actor objective: (a) prove or exhibit why
ceiling saturation persists even when the constraint gap narrows (does the
fixed step overshoot and pin at the ceiling, or does the actor objective's
nonconvexity keep the Lagrangian gradient pointing up?); (b) give the
condition under which a per-profile or scheduled multiplier would close
the residual to ≤1× (is the remaining 1.1–10.1× gap an optimization
failure or a structural infeasibility of the trajectory-level guard set
under the policy class?); (c) relate to the constrained-MDP hierarchy
already cited (expected episodic surrogate vs trajectory-level
reference-relative ceilings; discounted critic vs undiscounted 30-step
residual). Deliver: a quantitative dual-ascent analysis with a falsifiable
prediction the project could test on the frozen bundle.
**Data.** `reports/R424.md`, `reports/R425.md`, `reports/R427.md`,
`results/research_loop/r425_guard_constraints_signfix/formal_analysis.json`,
`results/research_loop/r427_critic_target_normalization/formal_analysis.json`,
learner source `src/andes_rl_kundur/agents/cd_matd3.py`.

### M2. Critic divergence: is it the causal driver of the common-frequency gap? (R421/R432/R435/R427)
**Fact.** R421/R432 diagnostics: R410-bundle CD runs show critic-loss
growth Q4/Q1 6.2–30.5 (and 24–126× on the pre-repair bundle), vanishing
actor gradient norms in 5/6 runs, a never-binding common-channel Lagrange
budget, and flat per-episode common cost. R435 refutes the multiplier
hypothesis (floor at 1.0 held; costs did not respond; 1/6 pairs improved)
and leaves critic divergence as the only surviving lead — as a hypothesis,
never a measured cause. R427's early transient shows Q4/Q1 155–326× at
8,640 steps before normalization brings it down.
**Question.** For twin-critic bootstrapped targets on this two-channel
reward (differential quadratic + common quadratic, discount 0.99), what
mechanism produces unbounded target growth here, and — the decisive
question — is there a formal reason divergence should corrupt the
common-frequency control channel specifically (e.g. critic
overestimation of common-mode returns → actor maximizes a wrong common
surrogate → aggressive common actions → worst-peak violations)? Deliver:
(a) a signed-overestimation/bias-propagation analysis for the two-channel
TD target with the registered normalization (0.15 Hz, 1.0 Hz/s scales and
the reward weights); (b) conditions under which bounded critics (clip /
normalization / target stabilization) provably bound the actor update;
(c) a testable prediction separating "divergence causes the gap" from
"divergence co-occurs with the gap".
**Data.** `reports/R421.md`, `reports/R432.md`, `reports/R435.md`,
`results/research_loop/r421_diagnostics/formal_analysis.json`,
`results/research_loop/r421_diagnostics/diagnostic_readout.json`,
`results/research_loop/r432_b3_diagnostics/train/*/seed*/diagnostics_summary.json`,
`results/research_loop/r435_multiplier_floor/formal_analysis.json`,
`results/research_loop/r427_critic_target_normalization/formal_analysis.json`.

### M3. Message-contrast sign puzzle: negative for CD-MATD3, positive for adapted SAC (R410/R431/R438)
**Fact.** Same Object A, same message structure (neighbour slots in the
7-slot observation row). CD-MATD3 family (repaired mask): message increment
−78.43% off-diagonal / −26.74% differential (R410, five-seed −74.98/−35.49).
Adapted-SAC family (slew-projected): message arm 0.635/0.590× the
deterministic reference with +25.0%/+34.1% contrast over the matched
no-message arm, and the message arm passes common-frequency + worst-peak
no-harm 20/20 blocks — the only arm in the whole family to do so (R431).
R438 channel isolation: the SAC contrast is carried primarily by the
**observation** channel (obs-only lands on the message side; reward-only
stays on the no-message side); the off-diagonal endpoint does not separate.
**Question.** Give a principled account of when identical neighbour
information yields negative vs positive coordination value: (a) formalize
the two learners' difference (CD-MATD3: joint critic + common/differential
cost heads + Lagrange multiplier; SAC: per-agent critic + sum of local
penalties) as an information-value problem (does the common-mode cost
structure of CD make neighbour observations confusable with own-state
drift, while the SAC reward's absolute-frequency term turns neighbour
observations into a common-mode correction signal?); (b) state the
condition (in terms of reward decomposition + critic architecture) under
which masking neighbours should HELP; (c) propose the minimal experiment
(arm design only, no execution) that would cleanly separate observation
value from reward value for the off-diagonal endpoint, fixing R438's
non-separation.
**Data.** `reports/R410.md`, `reports/R431.md`, `reports/R438.md`,
`results/research_loop/r410_message_repair/formal_analysis.json`,
`results/research_loop/r410_message_repair/endpoint_table.json`,
`results/research_loop/r431_sac_slew/formal_analysis.json`,
`results/research_loop/r438_sac_message_channels/formal_analysis.json`.

### M4. Why residual SAC on the verified energy-port anchor collapses to identity (R436)
**Fact.** Baseline-anchored residual SAC (zero residual = exact bandpass
$K=3.5$, reward $r_i=100r_f+50r_{abs}+0.0056r_H+0.0056r_D$, all terms
non-positive penalties): both arms pass every endpoint/guard on all 10
variants but sit within <0.003 of the anchor on $r_d$ and <0.005 on
$r_{\rm cross}$; no message contrast; NO-LEARNING-INCREMENT (CLM-1345).
**Question.** Why is identity a fixed point / local attractor of this
residual policy optimization? Conjecture: at zero residual the reward
terms are already at their baseline values and every deviation term is
non-positive, so the gradient landscape near identity is a sum of
downward-opening quadratics in the residual — identity is a local maximum
of the reward proxy. Verify or refute: compute the policy-gradient /
TD-target structure near zero residual for this reward + SAC on the frozen
environment; state the exact condition for identity to be locally optimal,
and whether any reward shape with the same physical intent could escape
it. (This converts "learning adds nothing here" from an observation to a
derivable statement.)
**Data.** `reports/R436.md`,
`results/research_loop/r436_energy_residual_sac/formal_analysis.json`,
`results/research_loop/r436_energy_residual_sac/variants/`,
learner `src/andes_rl_kundur/agents/sac.py`.

### M5. Time-varying headroom structure and the endpoint/action-stress trade-off (R416/R439/R441)
**Fact.** Static 21-law family: outcome-seeing oracle headroom = 0 (R416).
Time-varying oracle (30-step window, K∈{2,3,5} constant-gain segments from
the diagonal grid {(0.5,0.5),(1,1),(1.5,1.5),(2,2),(3,3)}): every profile
improves $r_d$ 9.3–14.4% and $r_{\rm cross}$ 7.6–11.9% over the static
winner km3_kd2 (R439). R441 guard completion: **all four winners collapse
to the constant schedule (3,3)** — no genuinely time-varying schedule was
selected — and every winner violates the action-stress no-harm budget
(action RMS +28.4–33.9%, total variation +10.5–16.9% vs the +10% budget)
while common-mode no-harm stays clean (CLM-1365).
**Question.** (a) Reinterpret: the measured "time-varying headroom" is a
single static gain point (3,3) — outside the static grid's damping range
({0.5,1,1.5,2}) — so the finding is grid-extension headroom, not
time-variation value. Confirm from the data and state the corrected
theorem-level phrasing for RQ2. (b) Formalize the observed trade-off:
is there a structural reason endpoint improvement on this object costs
action energy (e.g. larger M/D swings needed to shape the differential
response), and what is the minimal action-energy cost to reach
$r_d\le0.95$-style targets — a Lagrangian/Pareto formulation with the
measured points as anchors? (c) Pose the optimization problem for the
untested follow-up: "does a lower-action-stress winner exist in the
diagonal grid?" as a constrained search over the 5^K schedule space with
the R441 guard statistics as constraints; specify which stored quantities
are sufficient (only winners were re-run, so a full Pareto needs fresh
evaluations — state the minimal evaluation set).
**Data.** `reports/R416.md`, `reports/R439.md`, `reports/R441.md`,
`results/research_loop/r416_headroom_expansion/formal_analysis.json`,
`results/research_loop/r439_timevarying_oracle/` (analysis + 4 profiles),
`results/research_loop/r441_timevarying_guard/` (analysis + 4 profiles).

## Tier C — paper-grade proposition program (journal extension)

### C1. Controller-class certificate via FIR-Youla/SLS parameterization (§3.5/§6.4)
**State.** Manuscript §3.5 refuses a general tradeoff theorem (measured
point $r_d r_{\rm cross}=0.7013$ already violates the product-bound
candidate); §6.4 proposes a FIR-Youla/SLS search around a stable baseline
as future work; the theory-audit bundle rules that a controller-class
infeasibility statement is legitimate only with "a precisely bounded
stable convex class with an independently verified dual lower bound or
Farkas certificate". A demonstration solver exists
(`tmp/yang_md_decoupling_marl/vsg_v2_fir_response_solver.py`) but is a
blueprint, not a certificate.
**Question.** Construct the rigorous program: (a) a valid Youla/SLS
response parameterization for the frozen reduced swing model that (i)
guarantees internal stability of the resulting finite-order controllers,
(ii) makes the finite-window off-diagonal/differential energy constraints
affine or convex in the response variables, (iii) admits a strong dual so
that "no controller in class X achieves (r_d, r_cross) targets" is a
provable statement; (b) the exact class definition for which the
finite-family oracle results (R399/R416/R439) become a *certificate*
rather than a measurement; (c) the dual certificate computation recipe
and its verification checklist for the project's nonlinear headroom map
(the feasibility-native map is state-dependent — state the conditions
under which the linear certificate remains valid or must be relaxed).
**Data.** `manuscript/manuscript.md` (§3.5, §6.4),
`working/theory_audit_bundle/IMPORT_NOTE.md`,
`tmp/yang_md_decoupling_marl/vsg_v2_fir_response_solver.py`,
`tmp/yang_md_decoupling_marl/external_vsg_decoupling_certificate.py`,
`tmp/yang_md_decoupling_marl/vsg_v2_complete_resolution.md`.

## Intake contract (binding for every answer)

1. Classify every delivered item: (A) algebraic identity — must carry a
   derivation checkable by the repo; (M) mechanism prediction — must carry
   an observable-list (what sealed file, which field, which direction
   counts as support/refute); (P) paper-grade proposition — must carry
   assumption set, statement, proof sketch, and a verification plan.
2. All numbers must trace to the shipped sealed JSONs or be marked
   "hypothetical"; never back-fill.
3. Answers are design aids: nothing enters the manuscript or a feed
   before repo-side verification (the project's external-theory-intake
   contract, `skills/kundur-round/references/external-theory-intake.md`).
4. Priority order requested: P1, P2, P3 first (deadline 2026-09-07), then
   M3, M5, M4, M1, M2, then C1.
