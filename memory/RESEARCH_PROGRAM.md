---
version: 1
status: active
programme_id: tpwrs-vsg-graph-residual
current_phase: P2_topology_generalisation
north_star: >-
  Establish first whether physically bounded active-power and energy
  actuation creates material common-frequency-restoration authority beyond
  the current M/D-only proxy; only after that gate may a physics- and
  safety-constrained multi-timescale residual policy be tested against tuned
  classical baselines on unseen operating conditions and network topologies.
# Closed priority blocks archived verbatim in memory/RESEARCH_PROGRAM_CLOSED.md
# (2026-08-01, all closed through R292).  Add newly authorized questions below.
# YAML 书写: 条目文本禁含 ": " (冒号+空格会被解析成 mapping) — 用 "—" 替代.
priority_questions:
  - id: Q-0069
    rank: 1
    phase: P1_residual_mechanism
    objective: >-
      Determine whether a coupling-retaining predictor fitted only on R312
      predicts separately sealed unseen pulse amplitudes and operating
      conditions within prospective common/differential error bounds.
    required_reading:
      - memory/questions/Q-0069.md
      - memory/claims/CLM-0770.md
      - results/r312_model_first_stage1/analysis.json
      - results/r312_model_first_stage1/run_manifest.json
      - paper/decoupling_marl_model_first/working/model_contract.md
    verification:
      - Fit only on source-hash-verified R312 zero and paired-response records while retaining all estimated cross blocks.
      - Freeze new held-out amplitudes and operating conditions, endpoint errors, tolerances, and failure handling before execution.
      - Compare the coupling-retaining predictor with a matched block-diagonal ablation using identical fitting data and budget.
      - Require create-only held-out traces, source hashes, execution guards, and paired prediction reports before interpretation.
    scope_limits:
      - Predictor construction and prospective held-out validation only.
      - R312 is fitting evidence, not headline validation; no outcome-selected split or tolerance tuning.
      - No controller development, distributed-agent runtime, reward optimization, MARL, or neural training.
    stop_when:
      - The predictor is classified as PASS, NO-GO, or invalid held-out validation under the frozen rules.
phase_order:
  - P0_evidence_repair
  - P1_residual_mechanism
  - P2_topology_generalisation
  - P3_safety_and_stability
  - P4_high_fidelity_and_manuscript
---

# TPWRS-oriented research programme

## Accepted thesis

The existing per-topology algorithm search is Phase A: it established strong
baselines, a structural algorithm plateau, recurrent correctness risks, and a
droop/RL metric conflict.  R270/R271 then closed M/D-only control as a credible
complete common-frequency-restoration mechanism on the current proxy.

R272 implemented the first source-hashed, physically bounded active-power
proxy but was INVALID on its original disturbance bank.  R273 attributed the
shared baseline failures to that disturbance envelope rather than an
ESD1-only DAE confound.  R274 then prospectively generated and completion-
screened a new nontrivial signed, multi-location 24-case bank before any
controller trace, retained all 24 cases, and obtained a valid
AUTHORITY-POSITIVE result.  The frozen droop+PI storage layer reduced physical
VSG-mean IAE by 58.63% and final-window common absolute frequency by 77.29%,
with both endpoints improving in 24/24 pairs and every physical-contract guard
passing.

P0 is therefore closed for the explicit active-power authority question, and
Gate 2 may begin as a separate P1 mechanism test.  Gate 2 asks only whether a
prospectively frozen bounded fast M/D law adds independent RoCoF, peak,
synchronization, or inter-area value under the validated slow controller.
Residual learning, topology generalisation, and safety certification remain
unauthorized until their later gates are separately satisfied.

ANDES and the modified Kundur system remain the anchor environment.  SAC, TD3,
recurrent and Transformer variants remain historical baselines and ablations;
they are not active parallel paper theses.

## Phase gates

### P0 — Evidence repair and objective validity

- Retrain any headline recurrent baseline after the R261 target-alignment fix.
- Freeze physical-frequency provenance and separate common-mode restoration
  from differential-mode synchronisation.
- Convert the 11-axis `geo` score into a diagnostic dashboard, not the sole
  scientific endpoint.
- Use independent training seeds, a sealed disturbance bank, interval
  estimates, failure rates, and matched tuning/interaction budgets.

Exit only when the corrected baseline and evaluation protocol are sufficient
to test a new controller without retrospective metric selection.

### P1 — Residual mechanism

- Start from tuned droop as a stabilising prior.
- Learn a bounded residual and state-dependent gate.
- Ablate pure RL, fixed blends, residual without gating, and gated residual.
- Explain gains through common/differential frequency modes, control effort,
  saturation, and disturbance coupling.

Exit only with a reproducible mechanism result, not merely a higher composite
score.

### P2 — Topology generalisation

- Represent VSGs, buses, and electrical/communication links explicitly as a
  graph.
- Train shared policy parameters across multiple systems/topology variants.
- Seal entire held-out graphs, VSG counts, disturbance locations, and
  communication graphs for zero-/few-shot evaluation.

Exit only when a graph policy beats a size-matched non-graph policy on unseen
graphs with uncertainty estimates.

### P3 — Safety and stability

- Derive feasible inertia/damping regions or a certified safety projection.
- Report constraint violations, tail risk, and region-of-attraction or robust
  stability evidence.
- Stress delay, dropout, parameter error, low inertia, outages, and faults.

Exit only when safety is a measured or proved property rather than a reward
penalty.

### P4 — High fidelity and manuscript

- Reproduce at least one headline mechanism in another simulator or HIL/RTDS.
- Freeze data, configs, seeds, checkpoints, statistical scripts, and figures.
- Write the paper around system-level insight and falsifiable claims.

TPWRS is attempted only when the package contains lasting power-system insight,
not just an architecture comparison.

## Autonomous research policy

1. One active round and one falsifiable question at a time.
2. Resume an active round before selecting new work.
3. Select only questions listed in `priority_questions`; an unranked open
   question is not automatically part of the TPWRS programme.
4. Probe before training, and use kill/pivot gates to avoid compute-only search.
5. Never select a method because it is fashionable; every architecture must
   address a named failure mechanism and have a matched ablation.
6. Close every round with measured provenance, claim/question updates,
   validation, rendering, and the verbatim PI briefing.
7. Add the next priority question prospectively before opening its result.

## Kill and pivot rules

- Stop algorithm-only SOTA hunts on the fixed topology.
- A method that improves only an unfrozen or post-hoc composite does not pass.
- Two consecutive well-powered negative rounds on the same mechanism trigger a
  pivot review before another variant.
- A topology-general claim without entirely unseen graphs is rejected.
- A safety claim based only on average reward is rejected.

## Manuscript lines

Publication tracks register here, one line per manuscript.  Each line's
locked decisions, current state, pending forks, and asset pointers live in
its own LINE.md beside that manuscript's assets; its durable generated
documents are indexed by the adjacent ARTIFACTS.json.  Each active line owns
an exclusive write scope and may declare shared evidence as read-only.  This
section stays lean so future manuscript lines add exactly one line each.
Remove or archive a line at publication.

- [active, top priority 2026-07-30] ICEMS 2026 -> SCI journal extension.
  Current action, venue decision, evidence frontier, and all detailed pointers
  live only in `paper/sci_upgrade_survey/LINE.md`; experiment side is closed
  through R287 and no new experiment is authorized.
