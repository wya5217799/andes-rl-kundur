---
version: 1
status: active
programme_id: tpwrs-vsg-graph-residual
current_phase: P1_residual_mechanism
north_star: >-
  Establish first whether physically bounded active-power and energy
  actuation creates material common-frequency-restoration authority beyond
  the current M/D-only proxy; only after that gate may a physics- and
  safety-constrained multi-timescale residual policy be tested against tuned
  classical baselines on unseen operating conditions and network topologies.
priority_questions:
  - id: Q-0027
    rank: 10
    phase: P0_evidence_repair
    objective: >-
      Determine whether a pre-registered state-dependent droop residual gate
      can improve the learned-controller/droop Pareto frontier, using expanded
      physical endpoints and without interpreting legacy R201 as evidence for
      the corrected recurrent algorithm.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0027.md
      - memory/rounds/R261/verdict.md
      - memory/rounds/R262/verdict.md
      - docs/research/2026-07-24_rl_vsg_publication_landscape.md
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Probe frozen controllers before any new training.
      - Use real ANDES in WSL and preserve the V4 bit-identical contract.
      - Report geo and cum_rf as legacy diagnostics plus physical frequency endpoints.
      - Do not claim corrected recurrent performance from legacy checkpoints.
    stop_when:
      - Q-0027 has a recorded positive, negative, or partial verdict.
      - The round has a current claim with measured provenance.
      - The PI briefing and regenerated STATE.md identify the next programme question.
  - id: Q-0028
    rank: 20
    phase: P0_evidence_repair
    objective: >-
      Determine whether the R264 low-capacity mode-ratio gate improves paired
      physical frequency outcomes on a prospectively sealed random disturbance
      bank, without tuning on that bank and without using the paper-alignment
      composite as a primary endpoint.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0028.md
      - memory/rounds/R264/verdict.md
      - src/andes_rl_kundur/evaluation/paper_strict_eval.py
      - src/andes_rl_kundur/evaluation/physical_endpoints.py
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Freeze and hash the scenario bank before evaluating any controller.
      - Compare paired R201, droop k10, static alpha 0.25, and R264 gate alpha_cap 0.25 trajectories.
      - Use physical endpoints, normalized synchronization loss, failure rate, intervals, and tail outcomes.
      - Do not tune the gate threshold or capacity on the sealed bank.
      - Keep corrected recurrent retraining out of this replication round.
    stop_when:
      - Q-0028 has a positive, negative, or partial verdict from the sealed bank.
      - The result reports paired uncertainty, failures, and tail outcomes with measured provenance.
      - A next question explicitly chooses corrected residual training or a gate-mechanism pivot.
  - id: Q-0029
    rank: 30
    phase: P0_evidence_repair
    objective: >-
      Determine whether one prospectively fixed dynamic smoothing mechanism
      can retain the R265 gate's paired physical mean improvements while
      removing its action-variation failure on a new sealed disturbance bank.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0029.md
      - memory/rounds/R265/verdict.md
      - results/r265_sealed_gate_replication/sealed_gate_replication_summary.json
      - src/andes_rl_kundur/evaluation/hybrid.py
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Treat R264 and R265 as development evidence, not another confirmatory test.
      - Diagnose the action-variation mechanism before choosing a dynamic gate.
      - Freeze at most one smoothing law before generating new ANDES trajectories.
      - Keep ratio_full_scale 0.05 and alpha_cap 0.25; do not sweep them on R265.
      - Use a new sealed no-anchor bank and keep corrected recurrent training out of this pivot round.
    stop_when:
      - The action-variation source has a measured decomposition.
      - One pre-registered smooth gate has a positive, negative, or partial verdict on a new sealed bank.
      - The next question explicitly chooses corrected residual training or closes the hand-designed gate family.
  - id: Q-0030
    rank: 40
    phase: P0_evidence_repair
    objective: >-
      Determine whether a corrected, training/deployment-consistent bounded
      residual policy around a physical droop prior can show a reproducible
      physical mechanism benefit inside a prospectively defined
      reference-feasible disturbance envelope.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0030.md
      - memory/rounds/R261/verdict.md
      - memory/rounds/R267/verdict.md
      - src/andes_rl_kundur/agents/td3.py
      - src/andes_rl_kundur/agents/sac.py
      - src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py
      - scripts/train.py
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Treat this as a P0 correctness and feasibility pilot, not yet a P1 mechanism claim.
      - Reuse the corrected V4 and off-policy infrastructure before adding new machinery.
      - Start with a memoryless bounded residual; legacy recurrent checkpoints are mechanism evidence only.
      - Keep residual composition identical in training and evaluation.
      - Use a subtractive pilot kill gate before multi-seed training.
      - Define common baseline infeasibility separately from residual-specific failure.
      - Do not make topology, stability, cross-simulator, or manuscript claims in this question.
    stop_when:
      - Residual bounds, reset, checkpoint reload, and deterministic evaluation contracts are tested.
      - The pilot has a measured go or no-go verdict on predeclared physical and action guards.
      - A passed pilot has advanced to independent seeds and a sealed bank, or a failed pilot has closed the exact residual contract.
      - The round has a current claim, measured provenance, and a PI briefing.
  - id: Q-0031
    rank: 50
    phase: P0_evidence_repair
    objective: >-
      Determine whether a simple auditable residual-learning objective can
      align physical common-mode restoration, differential synchronization,
      and residual-specific effort/variation before authorizing a second
      controller training run.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0031.md
      - memory/rounds/R268/verdict.md
      - results/r268_residual_pilot_eval/pilot_summary.json
      - src/andes_rl_kundur/env/andes/base_env.py
      - src/andes_rl_kundur/env/andes/residual_adapter.py
      - src/andes_rl_kundur/evaluation/physical_endpoints.py
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Use existing R268 traces and synthetic tests before any new ANDES trajectory or training.
      - Keep physical common-mode, differential-mode, and residual-effort terms explicit and auditable.
      - Freeze one objective contract before a future training run; do not fit weights on its evaluation bank.
      - Do not sweep algorithms, seeds, horizons, hidden sizes, or residual scales in the objective-audit stage.
      - Keep topology, graph policy, stability, cross-simulator, and manuscript work out of this P0 question.
    stop_when:
      - The R268 reward/endpoint mismatch has a source-level and trace-level diagnosis.
      - One objective contract has passed or failed prospective unit, sign, and trajectory-ranking checks.
      - A positive audit authorizes one separate pilot, or a negative audit pivots away from learned residual control on this environment.
      - The round has a current claim, measured provenance, and a PI briefing.
  - id: Q-0032
    rank: 60
    phase: P0_evidence_repair
    objective: >-
      Determine whether the current bounded inertia/damping actuation admits a
      nontrivial controller-agnostic physical improvement margin above tuned
      droop on reference-feasible disturbances before any further learned
      controller work.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0032.md
      - memory/rounds/R268/verdict.md
      - memory/rounds/R269/verdict.md
      - results/r268_residual_pilot_eval/pilot_summary.json
      - src/andes_rl_kundur/evaluation/hybrid.py
      - src/andes_rl_kundur/evaluation/physical_endpoints.py
      - src/andes_rl_kundur/evaluation/paper_path.py
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Treat the disturbance-informed oracle as an attainability upper bound, never a deployable controller.
      - Freeze a low-dimensional physics-interpretable action schedule and strict evaluation budget before new trajectories.
      - Reuse the R268 feasible envelope, droop prior, physical endpoints, action bounds, and real-ANDES runner.
      - Do not train a neural network or sweep RL algorithms, seeds, hidden sizes, horizons, or rewards.
      - Keep topology, stability certification, cross-simulator, and manuscript work out of this P0 question.
    stop_when:
      - A prospective oracle budget and materiality threshold are frozen before new trajectories.
      - The attainable paired common/differential physical margin over droop is measured with safety and action guards.
      - A negative result closes learned inertia/damping control on this environment, or a positive result routes work to observability/credit assignment.
      - The round has a current claim, measured provenance, and a PI briefing.
  - id: Q-0033
    rank: 70
    phase: P0_evidence_repair
    objective: >-
      Determine whether material common-mode frequency restoration in the
      current modified Kundur model structurally requires an explicit
      active-power or secondary-frequency actuator beyond virtual inertia and
      damping.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0033.md
      - memory/rounds/R270/verdict.md
      - results/r270_attainable_oracle/attainable_oracle_summary.json
      - src/andes_rl_kundur/env/andes/base_env.py
      - src/andes_rl_kundur/env/andes/andes_vsg_env_v4.py
      - docs/research/2026-07-24_rl_vsg_publication_landscape.md
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Start with source, equilibrium, and existing-trajectory evidence; no new ANDES or model change until the actuator hypothesis is explicit.
      - Separate transient RoCoF, differential damping, and sustained common-frequency restoration.
      - Specify physical power, energy, state, and timescale limits before proposing any new actuator.
      - Do not train a neural network or reopen algorithm, reward, seed, amplitude, or duration sweeps.
      - Keep topology, stability certification, cross-simulator, and manuscript work out of this P0 audit.
    stop_when:
      - The current M/D and power/governor paths have an equation-level equilibrium interpretation.
      - R268/R270 traces quantify early and terminal common/differential effects by actuator direction.
      - The result either freezes one physically bounded new-actuator contract or pivots to model/benchmark correction.
      - The round has a current claim, measured provenance, and a PI briefing.
  - id: Q-0034
    rank: 80
    phase: P0_evidence_repair
    objective: >-
      Under a prospectively frozen power, energy, SOC, headroom, ramp, lag,
      efficiency, and converter-capability contract, determine whether one
      independently controlled classical active-power actuator improves both
      full-horizon physical VSG-mean IAE and final-window common-frequency
      absolute mean by at least 2% over a matched zero-active-power-support
      baseline with identical storage DAE structure, without worsening
      completion, synchronization, peak, RoCoF, action, or energy guards.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0034.md
      - memory/rounds/R270/verdict.md
      - memory/rounds/R271/verdict.md
      - memory/claims/CLM-0555.md
      - memory/claims/CLM-0560.md
      - memory/claims/CLM-0565.md
      - docs/research/2026-07-25_energy_feasible_multitimescale_vsg_landscape.md
      - docs/research/2026-07-25_energy_feasible_multitimescale_vsg_execution_plan.md
      - docs/eng-notes/NOTES_ANDES.md
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - /home/wya/andes_venv/bin/python for every real-ANDES smoke and formal trajectory
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Treat GENCLS plus an independent ESD1 as a hybrid actuator-authority proxy, not a unified physical GFM-BESS.
      - Source, derive, freeze, and hash every physical parameter and per-unit conversion before any new ANDES trajectory.
      - Freeze the existing M/D settings and compare classical active-power control against an identical-DAE zero-support baseline.
      - Use development cases only to select one primary classical controller, then evaluate it once on a new no-anchor sealed bank.
      - Do not train a neural network or start GNN, topology, stability-certificate, cross-simulator, HIL, or manuscript work.
    stop_when:
      - One frozen active-power contract has an AUTHORITY-POSITIVE, AUTHORITY-PARTIAL, NO-MATERIAL-AUTHORITY, or INVALID verdict.
      - Both co-primary endpoints, paired uncertainty, failures, safety, action, and energy/capability guards have measured provenance.
      - A positive result alone may open Gate 2; every other result diagnoses or closes the exact Gate-1 contract.
      - The round has a current claim, question closure, validation, rendering, and a PI briefing.
  - id: Q-0035
    rank: 90
    phase: P0_evidence_repair
    objective: >-
      Using completion and solver diagnostics only, determine whether R272's
      matched zero-support TDS failures are caused by an infeasible
      disturbance envelope, by the added zero-command ESD1 DAE, or by both,
      before any further active-power controller comparison.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0035.md
      - memory/rounds/R272/plan.md
      - memory/rounds/R272/verdict.md
      - memory/claims/CLM-0570.md
      - results/r272_active_power_authority_v2/active_power_authority_summary.json
      - results/r272_active_power_authority_v2/provenance.json
      - docs/eng-notes/NOTES_ANDES.md
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - /home/wya/andes_venv/bin/python for every real-ANDES diagnostic trajectory
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Diagnose original V4 versus identical-DAE zero support only; do not run droop+PI or learning.
      - Keep M/D, storage contract, capacity, placement, solver configuration, timing, and environment seed frozen.
      - Retain every failure and use no candidate-performance endpoint to select a future envelope.
      - Do not open Gate 2, topology, stability-certificate, cross-simulator, HIL, or manuscript work.
    stop_when:
      - The registered shared failures and signed complete controls have matched V4 versus zero-support DAE evidence.
      - The cause is classified ENVELOPE-INFEASIBLE, STORAGE-DAE-CONFOUND, MIXED, or UNRESOLVED/INVALID.
      - Any future feasible envelope or model repair is explicit, prospective, and separate from an authority re-test.
      - The round has a current claim, measured provenance, question update, validation, rendering, and a PI briefing.
  - id: Q-0036
    rank: 100
    phase: P0_evidence_repair
    objective: >-
      Determine whether the frozen R272 active-power controller has valid
      bank-level common-frequency-restoration authority on a new signed,
      multi-location scenario bank whose zero-support feasibility,
      exclusions, and nontriviality are prospectively frozen before any
      controller trajectory.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0036.md
      - memory/rounds/R272/verdict.md
      - memory/rounds/R273/verdict.md
      - memory/claims/CLM-0570.md
      - memory/claims/CLM-0575.md
      - results/r273_storage_dae_feasibility/storage_dae_feasibility_summary.json
      - results/r273_storage_dae_feasibility/boundary_summary.json
      - src/andes_rl_kundur/evaluation/feasibility_screen.py
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - /home/wya/andes_venv/bin/python for every real-ANDES screening and controller trajectory
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Freeze zero-support feasibility and bank nontriviality before any controller trajectory; retain and stratify every exclusion.
      - Reuse the exact frozen R272 droop+PI, storage, M/D, solver, horizon, and physical endpoint contracts.
      - Do not inspect controller endpoints while generating or screening the bank, and do not tune after the formal seal.
      - Do not train learning, change the actuator, or open Gate 2, topology, stability-certificate, cross-simulator, HIL, or manuscript work.
    stop_when:
      - The prospective bank has an immutable feasibility/nontriviality contract and retained exclusion accounting.
      - One sealed comparison has an AUTHORITY-POSITIVE, AUTHORITY-PARTIAL, NO-MATERIAL-AUTHORITY, or INVALID verdict.
      - Completion, physical endpoints, paired uncertainty, tail risk, action, SOC, power, energy, ramp, and capability guards have measured provenance.
      - The round has a current claim, question update, validation, rendering, and a PI briefing.
  - id: Q-0037
    rank: 110
    phase: P1_residual_mechanism
    objective: >-
      Determine whether one prospectively frozen, bounded fast M/D law adds
      independent physical transient value under the validated R274 slow
      droop+PI active-power controller, without weakening common-frequency
      restoration, completion, action, energy, or safety guards.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0037.md
      - memory/rounds/R270/verdict.md
      - memory/rounds/R271/verdict.md
      - memory/rounds/R274/verdict.md
      - memory/claims/CLM-0555.md
      - memory/claims/CLM-0565.md
      - memory/claims/CLM-0580.md
      - results/r274_prospective_active_power_authority/active_power_authority_summary.json
      - docs/research/2026-07-25_energy_feasible_multitimescale_vsg_execution_plan.md
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - /home/wya/andes_venv/bin/python for every real-ANDES formal trajectory
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Keep the R274 slow droop+PI, storage, bank, solver, horizon, and physical-frequency contracts identical in both arms.
      - Freeze one bounded fast M/D law and its amplitude, rate, and action budgets before formal trajectories.
      - Register physical RoCoF, peak, synchronization, and inter-area endpoints while guarding slow restoration, completion, SOC, power, energy, and constraints.
      - Do not train learning, change topology, alter the active-power actuator, or claim unified GFM-BESS, stability, EMT, HIL, or deployment evidence.
    stop_when:
      - One sealed comparison has a FAST-LAYER-POSITIVE, FAST-LAYER-PARTIAL, NO-INDEPENDENT-FAST-VALUE, or INVALID verdict.
      - Fast endpoints, paired uncertainty, tail risk, M/D action, completion, slow-restoration, and storage-contract guards have measured provenance.
      - A non-positive result explicitly removes or narrows the fast-layer research claim.
      - The round has a current claim, question update, validation, rendering, and a PI briefing.
  - id: Q-0039
    rank: 111
    phase: P1_residual_mechanism
    objective: >-
      Determine whether the validated R275 fast/slow benefit contains a
      material non-additive interaction, by adding only the missing fast-only
      arm and reusing the immutable R274 zero/slow and R275 combined traces.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0039.md
      - memory/rounds/R274/verdict.md
      - memory/rounds/R275/verdict.md
      - memory/claims/CLM-0580.md
      - memory/claims/CLM-0585.md
      - results/r274_prospective_active_power_authority/provenance.json
      - results/r275_fast_md_authority/fast_md_authority_summary.json
      - results/r275_fast_md_authority/provenance.json
      - docs/research/2026-07-25_energy_feasible_multitimescale_vsg_execution_plan.md
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - /home/wya/andes_venv/bin/python for every real-ANDES formal trajectory
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Reuse the exact R274 formal bank, zero-support and slow-only traces, plus the exact R275 combined traces, by immutable hash.
      - Add exactly one fast-only arm with the frozen R275 common_M_pos law and zero requested BESS active power on the identical storage DAE.
      - Freeze absolute-scale factorial interactions, best-single comparisons, paired uncertainty, tail risk, action, completion, and storage guards before the first new trace.
      - Use three disjoint WSL shards; do not rerun existing arms, train learning, tune controllers, change topology/actuators, or claim non-additivity from combined-versus-slow evidence alone.
    stop_when:
      - One sealed four-arm comparison has a NONADDITIVE-POSITIVE, NONADDITIVE-PARTIAL, ADDITIVE-ONLY, or INVALID verdict.
      - The factorial interaction, best-single contrasts, completion, fast/slow endpoints, tail, action, storage, and provenance guards have measured evidence.
      - An additive-only result explicitly retains the two layers only as a classical benchmark and blocks learning novelty on their interaction.
      - The round has a current claim, question update, validation, rendering, and a PI briefing.
  - id: Q-0040
    rank: 112
    phase: P1_residual_mechanism
    objective: >-
      Determine whether an explicitly optimistic outcome-seeing oracle over a
      frozen zero-sum inertia basis has a material, guarded differential-mode
      margin above the immutable R274+R275 additive classical reference before
      any parallel multi-seed residual training.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0040.md
      - memory/rounds/R270/verdict.md
      - memory/rounds/R275/verdict.md
      - memory/rounds/R276/verdict.md
      - memory/claims/CLM-0555.md
      - memory/claims/CLM-0585.md
      - memory/claims/CLM-0590.md
      - results/r275_fast_md_authority/fast_md_authority_summary.json
      - results/r276_fast_slow_factorial/fast_slow_factorial_summary.json
      - docs/research/2026-07-25_energy_feasible_multitimescale_vsg_execution_plan.md
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - /home/wya/andes_venv/bin/python for every real-ANDES candidate trajectory
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Reuse the exact R275 combined traces, R274 formal bank, plant, slow controller, common pulse, solver, horizon, physical endpoint, action, and storage contracts by immutable hash.
      - Add only six signed directions spanning the four-agent zero-sum inertia subspace, with one frozen amplitude and the same 15-step fast window.
      - Treat the result-seeing selector only as a development upper bound; it is not a deployable controller, confirmatory population evidence, or a paper result.
      - Use at most eight disjoint WSL ANDES shards after measured CPU/memory preflight; do not train learning, tune amplitude/duration, change topology/actuators, or inspect candidate endpoints before the library is complete.
    stop_when:
      - One sealed library-oracle audit has a LEARNING-GAP-PRESENT, LEARNING-GAP-PARTIAL, NO-RL-NEEDED, or INVALID verdict.
      - Both differential endpoints, paired uncertainty, common/restoration guards, tail risk, completion, exact zero-sum action, storage, and provenance have measured evidence.
      - A no-gap result closes or abandons Q-0038 without neural training; a positive result freezes exactly one learning gap before training.
      - The round has a current claim, question update, validation, rendering, and a PI briefing.
  - id: Q-0038
    rank: 113
    phase: P1_residual_mechanism
    objective: >-
      Complete the minimum honest ICEMS evidence gate by training exactly one
      memoryless parameter-shared multi-agent policy whose only learned action
      is a bounded, slew-limited scalar on the two-area zero-sum inertia mode,
      and test whether it materially improves differential synchronization
      above the immutable R274+R275 classical reference on fresh unseen cases.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0038.md
      - memory/rounds/R261/verdict.md
      - memory/rounds/R274/verdict.md
      - memory/rounds/R275/verdict.md
      - memory/rounds/R276/verdict.md
      - memory/rounds/R277/verdict.md
      - memory/claims/CLM-0595.md
      - docs/research/2026-07-26_icems_2026_minimal_full_paper_experiment_plan.md
      - results/r277_learning_gap_oracle/learning_gap_oracle_summary.json
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - /home/wya/andes_venv/bin/python for every real-ANDES pilot and formal trajectory
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Keep the submitted title unchanged during the experiment and treat positive MARL evidence as a prerequisite for retaining its final phrase.
      - Freeze the R274 slow droop+PI storage controller and R275 common-inertia pulse; the learned action is only q times [1, 1, -1, -1], with D fixed at zero.
      - Use the viewed R274-R277 bank only for development and contract checks; generate and seal a fresh 24-case formal bank after all checkpoints are frozen.
      - Run one pilot seed first and continue to exactly three reported seeds only if the prospective pilot gate passes.
      - Use one memoryless algorithm and one frozen reward contract; no HAWE, ensemble, recurrent policy, algorithm sweep, best-seed headline, topology work, or navigation-layer expansion beyond baseline reproducibility fixes.
    stop_when:
      - The single-seed pilot fails either registered differential endpoint, any common/restoration/action/storage/completion guard, or the implementation contract.
      - Or three frozen seeds complete one fresh sealed 24-case comparison with a MARL-RESIDUAL-POSITIVE, NO-ADAPTIVE-MARL-VALUE, or INVALID verdict.
      - The result is propagated to the ICEMS manuscript without rescuing a negative outcome through new algorithms, seeds, rewards, weak baselines, or HAWE.
      - The round has a current claim, question update, validation, rendering, PI briefing, and committed code/provenance.
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
