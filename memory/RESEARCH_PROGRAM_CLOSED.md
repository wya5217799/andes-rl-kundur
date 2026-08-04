# RESEARCH_PROGRAM closed-priority archive

> Archived 2026-07-29: all 15 priority_question blocks (Q-0027..Q-0042) were
> closed through R281 and were removed from `memory/RESEARCH_PROGRAM.md` to
> keep the session-start file lean.  Verbatim content below; the live policy
> and any newly authorized questions stay in the main file.  Nothing here is
> parsed by tools.

```yaml
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
  - id: Q-0041
    rank: 114
    phase: P1_residual_mechanism
    objective: >-
      Determine whether one prospectively frozen causal inter-area feedback
      law or a size-matched centralized scalar TD3 explains the R278
      parameter-shared-policy signal, and quantify empirical common/differential
      leakage on fresh disturbances before any stronger decoupling or MARL claim.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0041.md
      - memory/rounds/R278/verdict.md
      - quality_reports/ars_icems2026_review/00_synthesis.md
      - src/andes_rl_kundur/agents/shared_area_td3.py
      - src/andes_rl_kundur/env/andes/icems_residual_env.py
      - results/r278_icems_residual_pilot_s49/icems_residual_pilot_summary.json
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - /home/wya/andes_venv/bin/python for every real-ANDES trajectory
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Treat this as a new reviewer-driven identifiability study; never reopen, overwrite, or reinterpret the stopped R278 gate.
      - Freeze at most one causal feedback family and one size-matched centralized actor contract before formal evaluation.
      - Match observations, scalar action, reward, training steps, predeclared seeds, and tuning budget between shared and centralized actors.
      - Freeze every controller before generating and screening a fresh signed, multi-location formal bank.
      - Do not use HAWE, recurrent policies, reward or algorithm sweeps, topology changes, EMT, HIL, deployment claims, or manuscript edits.
    stop_when:
      - One valid verdict classifies the signal as MARL-IDENTIFIABLE-POSITIVE, CAUSAL-EXPLANATION-SUFFICIENT, CENTRALIZED-EXPLANATION-SUFFICIENT, NO-REPRODUCIBLE-LEARNED-VALUE, or INVALID.
      - Algebraic inertia-budget preservation is separated explicitly from measured dynamic common/differential leakage.
      - All seeds, fresh-bank cases, paired or hierarchical uncertainty, failures, tail risk, action, storage, completion, and provenance guards are retained.
      - The round has a current claim, question update, validation, rendering, and a PI briefing.
  - id: Q-0042
    rank: 120
    phase: P1_residual_mechanism
    objective: >-
      Determine whether static differential inertia allocation along the
      frozen two-area zero-sum mode produces a material, monotone mapping to
      the identified inter-area mode damping ratio in the linearized modified
      Kundur model, gating the SCI journal-extension mechanism section.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0042.md
      - memory/rounds/R280/verdict.md
      - memory/claims/CLM-0610.md
      - paper/sci_upgrade_survey/REPORT.md
      - docs/eng-notes/NOTES_ANDES.md
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - /home/wya/andes_venv/bin/python for every ANDES linearization
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Analysis-first: eigenvalue linearization plus existing traces; no new training, no new time-domain bank, no topology change.
      - Freeze the plant, R274 slow layer, R275 common pulse, operating point, action coordinate, sweep grid, and mode-identification rule before the first eigenvalue.
      - Sweep only static |q| <= 0.25 along [1, 1, -1, -1] plus one predeclared heterogeneity axis at development level.
      - Compare mapping shape to R280 gains only qualitatively; never fit parameters to force agreement.
      - Do not edit the manuscript or make topology, stability-certificate, cross-simulator, or HIL claims in this round.
    stop_when:
      - One sealed sweep has a MECHANISM-CONFIRMED, MECHANISM-PARTIAL, MECHANISM-ABSENT, or INVALID verdict.
      - The damping-ratio mapping, mode identification, materiality threshold, and provenance have measured evidence.
      - An absent result degrades the SCI plan to the pure-empirical track prospectively.
      - The round has a current claim, question update, validation, rendering, and a PI briefing.
  # Archived 2026-07-29: Q-0043 closed-positive @ R283 by CLM-0630
  # (STRENGTH-GRADIENT-CONFIRMED).
  - id: Q-0043
    rank: 130
    phase: P1_residual_mechanism
    objective: >-
      Determine how differential-allocation damping sensitivity varies with
      prospectively frozen grid-strength axes — aggregate VSG inertia scaling
      and tie-line reactance scaling as the declared SCR proxy — on the
      frozen modified Kundur plant, providing the measured gradient for the
      SCI journal extension's weak-grid validation section.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0043.md
      - memory/rounds/R281/verdict.md
      - memory/claims/CLM-0615.md
      - paper/sci_upgrade_survey/LINE.md
      - docs/eng-notes/NOTES_ANDES.md
    verification:
      - python memory/tools/round_preflight.py --latest
      - python memory/tools/dual_metric_lint.py
      - python -m pytest tests -q
      - /home/wya/andes_venv/bin/python for every ANDES linearization
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Analysis first — eigenvalue linearization on the frozen R281 plant; no new training, no new time-domain bank, no topology change.
      - Freeze both grid-strength axes (inertia-scaling set, tie-line reactance-scaling set as the declared SCR proxy) and the q subset before the first eigenvalue.
      - Reuse the R281 conjugate-pair-merged per-machine participation mode-identification rule in-script; do not re-tune it on results.
      - Compare sensitivity across strength levels qualitatively against R281 only; never fit parameters to force a gradient.
      - Do not edit the manuscript or make topology, stability-certificate, cross-simulator, or HIL claims in this round.
    stop_when:
      - One sealed sweep has a STRENGTH-GRADIENT-CONFIRMED, STRENGTH-GRADIENT-PARTIAL, STRENGTH-GRADIENT-ABSENT, or INVALID verdict.
      - The sensitivity-vs-strength mapping, SCR-proxy contract, mode identification, and provenance have measured evidence.
      - An absent result narrows the C2 weak-grid section to the R281 development-probe statement prospectively.
      - The round has a current claim, question update, validation, rendering, and a PI briefing.
  # Archived 2026-07-29: Q-0044 closed-positive @ R285 by CLM-0640
  # (ZONE-CHARTED).
  - id: Q-0044
    rank: 140
    phase: P1_residual_mechanism
    objective: >-
      Chart the inter-area / VSG-local mode hybridization zone on the frozen
      modified Kundur plant at low aggregate VSG inertia — map where the
      pre-registered branch-validity screen flags identification failure
      across a dense M0 x q grid and attribute which mode families mix, so
      the C2 weak-grid section can state precisely where the inertia-axis
      gradient is measurable.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0044.md
      - memory/rounds/R283/verdict.md
      - memory/rounds/R283/execution_amendment_20260729.md
      - memory/claims/CLM-0630.md
      - paper/sci_upgrade_survey/LINE.md
    verification:
      - python memory/tools/round_preflight.py --latest
      - python -m pytest tests -q
      - /home/wya/andes_venv/bin/python for every ANDES linearization
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Analysis first — eigenvalue linearization on the frozen R281 plant; no new training, no new time-domain bank, no topology change.
      - Freeze the M0 x q grid (M0 in {100,125,150,175} x q in {-0.25,-0.125,0,+0.125,+0.25}) before the first eigenvalue; R283 endpoint rows at M0 in {100,150} are reused read-only for the map, and the three flagged R283 cells may be re-computed solely to record the full merged-mode list for attribution — they must reproduce R283 identified values within |dzeta| < 1e-6, else INVALID.
      - Reuse the R282/R283 identification rule and branch-validity screen unchanged; no new mode-tracking rule this round.
      - Do not edit the manuscript or make topology, stability-certificate, cross-simulator, or HIL claims in this round.
    stop_when:
      - One sealed map has a ZONE-CHARTED, ZONE-PARTIAL, or INVALID verdict.
      - The valid/flag boundary and the mode-family attribution have measured evidence.
      - The round has a current claim, question update, validation, rendering, and a PI briefing.
```

  # Archived 2026-07-29: Q-0045 closed-positive @ R286 by CLM-0645
  # (SURVIVES).
  - id: Q-0045
    rank: 150
    phase: P1_residual_mechanism
    objective: >-
      Test in time domain whether the frozen centralized differential-
      allocation gain (CLM-0610, sealed R279 bank) survives a weakened
      inter-area tie corridor — rerun frozen arms q0 + centralized
      s17/s53/s89 on the same 24 sealed scenarios with the 7<->8 triple-
      circuit corridor r/x scaled by k in {1.5, 2.0}, judge by the pre-
      registered tree SURVIVES / DEGRADED / COLLAPSES / INVALID, and group
      the same traces by disturbance location for a descriptive location-
      dependence read.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0045.md
      - memory/claims/CLM-0610.md
      - memory/rounds/R279/verdict.md
      - paper/sci_upgrade_survey/LINE.md
    verification:
      - python memory/tools/round_preflight.py --latest
      - python -m pytest tests -q
      - /home/wya/andes_venv/bin/python for every ANDES time-domain run
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Zero-training transfer evaluation only — frozen R279 controllers and checkpoints; no retraining, no new controller, no reward change.
      - Do not modify andes_vsg_env_v4.py, andes_vsg_storage_env.py, r279_controllers.py, or the sealed formal_bank.json — weak-tie variant lives in a new env subclass file; scenarios are referenced read-only with hash verification.
      - Tie scaling limited to TIE_IDX = Line_4/Line_5/Line_6 r and x multiplied by k in {1.5, 2.0}, applied after setup and before PFlow exactly as in probes/eig_alloc_common.py; no other plant parameter touched.
      - Arms frozen prospectively — q0 plus centralized s17/s53/s89 (4 arms); if wall-clock pressure forces cuts, drop k=1.5 first, then reduce to centralized s17 only; never cut q0 or the endpoint set.
      - Disturbance-location analysis is descriptive grouping of existing and new traces by the bank location field — no model fitting, no new scenarios.
      - Retraining under weakened tie is not this round — the tree may open it as a follow-up question, nothing more.
    stop_when:
      - One sealed weak-grid evaluation has a SURVIVES, DEGRADED, COLLAPSES, or INVALID verdict.
      - The per-location grouped endpoint read has measured evidence at every k level actually run.
      - The round has a current claim, question update, validation, rendering, and a PI briefing.

  # Archived 2026-07-30: Q-0046 closed-positive @ R287 by CLM-0650
  # (SURVIVES).
  - id: Q-0046
    rank: 160
    phase: P1_residual_mechanism
    objective: >-
      Stress-test the sealed CLM-0645 weak-corridor survival boundary without
      retraining -- rerun the frozen q0 and centralized s17/s53/s89 arms on the
      same sealed 24-scenario bank with the same Line_4/5/6 corridor scaling
      extended only to k in {2.5, 3.0}, preserve the R286 endpoints, guards,
      and SURVIVES / DEGRADED / COLLAPSES / INVALID decision tree, and stop at
      sealed evidence plus the project feed.
    required_reading:
      - memory/STATE.md
      - memory/questions/Q-0046.md
      - memory/claims/CLM-0645.md
      - memory/rounds/R286/plan.md
      - results/r286_weak_grid_td/weak_tie_summary.json
      - paper/sci_upgrade_survey/LINE.md
    verification:
      - python memory/tools/round_preflight.py --latest
      - python -m pytest tests -q
      - /home/wya/andes_venv/bin/python for every ANDES time-domain run
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Zero-training boundary extension only -- no training, controller change, reward change, seed selection, or new architecture.
      - Reuse the hash-verified R279 24-scenario bank, q0 plus centralized s17/s53/s89, and the R286 weak-tie environment definition without modification.
      - Change only the declared Line_4/5/6 corridor r and x multiplier to k in {2.5, 3.0}; do not add a second corridor definition or convert the proxy to SCR units.
      - Preserve the R286 physical endpoints, statistics, action and storage guards, injection audit, failure retention, and immutable artifact rules.
      - Disturbance-location output is descriptive only; no significance claim and no new scenarios.
      - Do not write or modify LaTeX, manuscript prose, polished figures, venue files, or any other manuscript asset.
    stop_when:
      - One seal-first 192-trajectory matrix has a SURVIVES, DEGRADED, COLLAPSES, or INVALID decision, with every failed trajectory retained.
      - The strongest bounded result and its prohibited stronger forms are recorded in at most the existing project feed plus required round ledger cards.
      - No training or manuscript-writing branch is opened automatically.

  # Archived 2026-07-30: Q-0047 closed-partial @ R290 by CLM-0665
  # (ROOT-CAUSE-BOUNDED-NO-VALID-PATH).
  - id: Q-0047
    rank: 170
    phase: P1_residual_mechanism
    objective: >-
      Diagnose the R289 validity failure before any new topology-value matrix.
      Build a fast WSL q0-only feedback loop for nominal and the sealed Line_2
      outage; distinguish order-serialization drift, incorrect post-setup line
      status application, failed DAE/EIG initialization, and a genuine
      positive-real mode. Make the seal action order an explicit list, make
      initialization success and residuals hard guards, add regression tests,
      and stop with a bounded diagnostic feed. Do not repeat or reinterpret
      the R289 4x7 matrix.
    required_reading:
      - memory/questions/Q-0047.md
    verification:
      - python memory/tools/round_preflight.py --latest
      - python -m pytest tests -q
      - /home/wya/andes_venv/bin/python for every ANDES PFlow and EIG run
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - No training, GNN, reward/controller change, checkpoint selection, or algorithm sweep.
      - Preserve every R288/R289 plan, seal, artifact, claim, feed, and verdict; no formal retry, deletion, overwrite, or post-hoc reclassification.
      - Use q0 only and the already sealed Line_2 diagnostic target. TDS initialization may be invoked as an initialization check, but no time integration, 4x7 matrix, alternative circuit, action comparison, training, or controller evaluation is allowed.
      - The diagnostic may compare topology-application/setup mechanisms one variable at a time. It must record initialization return state, residual evidence, line status, PFlow, and eigenvalue real parts.
      - No damping, headroom, stability, topology-value, topology-generalization, safety, or deployability claim may be produced.
      - Do not write or modify LaTeX, manuscript prose, polished figures, or venue files.
    stop_when:
      - A deterministic minimal reproducer identifies or sharply bounds the R289 initialization and positive-real failure mechanism.
      - Explicit action-order serialization and the valid topology-initialization path have red-then-green regression coverage, or the absence of a safe path is formally recorded.
      - The round has a pointer-first diagnostic feed, current claim, question update, validation, rendering, and verbatim PI briefing; no value-matrix, learning, or time-domain follow-up is opened automatically.

  # Archived 2026-07-30: Q-0048 closed-negative @ R291 by CLM-0670
  # (NO-HANDOFF-VALUE).
  - id: Q-0048
    rank: 10
    phase: P1_residual_mechanism
    objective: >-
      Determine whether a prospectively frozen deterministic state-aware,
      hysteretic, slew-limited handoff of the validated fast common-inertia
      support to the frozen slow droop-PI BESS layer provides timing-specific
      value beyond fixed 3 s and fixed 5 s schedules on a fresh sealed bank.
    required_reading:
      - memory/questions/Q-0048.md
      - memory/rounds/R291/plan.md
      - memory/claims/CLM-0590.md
      - src/andes_rl_kundur/evaluation/fast_md_authority.py
      - paper/icems2026/LINE.md
    verification:
      - python memory/tools/round_preflight.py R291
      - python -m pytest tests/test_state_aware_handoff.py -q
      - python -m pytest tests -q
      - python memory/tools/feed_check.py paper/icems2026/reports/R291.md
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - No RL training, learned switching, GNN, MARL redesign, or horizon extrapolation.
      - Keep V4, storage plant, slow controller, fast amplitude, solver, and physical endpoints frozen.
      - Use five matched arms so state information is separable from longer support duration.
      - Freeze thresholds, bank, statistics, action budgets, and kill gates before any formal trace.
      - Retain every generated scenario and every failed or forced-release trajectory.
    stop_when:
      - Q-0048 has a positive, negative, partial, or invalid verdict from the sealed five-arm bank.
      - Timing value is separated from duration value using fixed 3 s and fixed 5 s comparators.
      - The result has measured provenance, paired uncertainty, tail and physical guards, a feed, claim, and PI briefing.

  # Archived 2026-08-01: Q-0049 closed-partial @ R292 by CLM-0675
  # (INVALID).
  - id: Q-0049
    rank: 10
    phase: P1_residual_mechanism
    objective: >-
      Determine whether a prospectively frozen neighbour-only distributed
      edge policy with decentralized execution retains reproducible
      differential-allocation value against q0 and a matched joint-observation
      centralized vector actor when both learned controllers share the same
      three-coordinate zero-sum action space, training budget, physical
      constraints, seeds, and fresh evaluation bank.
    required_reading:
      - memory/questions/Q-0049.md
      - memory/rounds/R292/plan.md
      - memory/claims/CLM-0610.md
      - src/andes_rl_kundur/agents/shared_area_td3.py
      - src/andes_rl_kundur/env/andes/icems_residual_env.py
      - src/andes_rl_kundur/control/area_inertia_residual.py
    verification:
      - python memory/tools/round_preflight.py R292
      - python -m pytest tests/test_vector_residual_control.py tests/test_vector_residual_td3.py -q
      - python -m pytest tests -q
      - /home/wya/andes_venv/bin/python for every real-ANDES trajectory
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Freeze the path communication graph, local observation, edge-flow action contract, reward, seeds, budgets, endpoints, guards, and decision tree before any real-ANDES controller trace.
      - Distributed execution may use endpoint-neighbour messages only; a centralized critic is training-only and no centrally aggregated action is allowed.
      - Compare q0, centralized-vector TD3, and distributed-edge TD3 only; no algorithm, reward, hidden-size, seed, or communication-graph sweep.
      - Generate and seal a fresh signed multi-location 24-case bank only after all six checkpoints are frozen; retain every failure and exclusion.
      - Keep V4, the validated slow storage layer, the fixed common pulse, and physical 60-Hz reporting unchanged.
      - Do not edit either manuscript line or claim topology, communication robustness, stability, EMT/HIL, or deployment transfer.
    stop_when:
      - Engineering stability fails before formal execution and the exact contract is closed without performance rescue.
      - Or three fixed seeds per architecture complete one fresh sealed seven-arm comparison with a bounded positive, inferior, unresolved, no-value, or invalid verdict.
      - The result reports hierarchical uncertainty, per-seed directions, all physical/action/storage/completion/tail guards, immutable provenance, and the verbatim PI briefing.

  # Archived 2026-08-02: Q-0051 closed-partial @ R294 by CLM-0680
  # (MODEL-FIRST-DISTRIBUTED-BASELINE-VALIDATED-PARTIAL).
  - id: Q-0051
    rank: 10
    phase: P1_residual_mechanism
    objective: >-
      Determine which control-oriented reduction of the full ANDES DAE can
      preserve common-frequency, RoCoF, inter-area, storage, constraint, and
      cross-coupling behavior across declared operating points, and use it to
      identify a constrained neighbour-distributed controller before any new
      neural policy is trained.
    required_reading:
      - memory/questions/Q-0051.md
      - memory/claims/CLM-0565.md
      - memory/claims/CLM-0580.md
      - memory/claims/CLM-0585.md
      - memory/claims/CLM-0615.md
      - src/andes_rl_kundur/env/andes/andes_vsg_storage_env.py
      - src/andes_rl_kundur/control/active_power.py
    verification:
      - python memory/tools/round_preflight.py R294
      - primary-source model and controller memo with equation-to-source bindings
      - registered non-learning model-validation protocol before any ANDES probe
      - python memory/tools/validate.py
      - python memory/tools/render.py
    scope_limits:
      - Treat full ANDES as the truth model and every LTI, LPV, modal, nonlinear, or graph model as a hypothesis requiring validation.
      - Do not assume exact common--differential decoupling or a fixed fast--slow handoff; quantify cross-coupling and time-scale separation.
      - Compare active-power, inertia, and damping authority before freezing the action set.
      - Require local physical states, local actions, explicit neighbour messages, and decentralized execution for any multi-agent formulation.
      - No neural training, architecture comparison, manuscript claim, topology-generalization, stability, EMT-HIL, or deployment claim in this modeling gate.
    stop_when:
      - One model family is selected or rejected by explicit structural and simulation-validation criteria.
      - The allowed multi-agent scientific object, controller synthesis problem, residual coupling measure, actuator set, and neural-entry gate are written explicitly.
      - The next experiment, if any, is a non-learning model-validation probe frozen before execution.

  # Archived 2026-08-02: Q-0052 closed-negative @ R295 by CLM-0685
  # (CONSENSUS-TIMESCALE-NO-GO).
  - id: Q-0052
    rank: 1
    phase: P1_residual_mechanism
    objective: >-
      Determine whether graph-spectral tuning of the explicit neighbour-only
      DAPI consensus time scale reduces its residual fast inter-area penalty
      without erasing synchronization benefit or harming common-frequency and
      storage-constraint guards.
    required_reading:
      - memory/questions/Q-0052.md
      - memory/claims/CLM-0680.md
      - memory/rounds/R294/verdict.md
      - results/r294_model_validation/round_summary.json
      - src/andes_rl_kundur/control/decentralized_dapi.py
    verification:
      - Seal one development-only matched bank before simulation.
      - Execute consensus gains 1, 2, and 4 per second with explicit local agents.
      - Require all completion, physical, action, and storage guards.
      - Select only a candidate meeting the frozen fast, synchronization, and common gates.
    scope_limits:
      - Development-only fixed-modified-Kundur mechanism diagnosis.
      - No neural, manuscript, topology, safety, stability, deployment, MARL,
        or architecture-superiority claim.
    stop_when:
      - A candidate passes and becomes eligible for separate held-out confirmation.
      - Both candidates fail and consensus-gain tuning stops.

  # Archived 2026-08-02: Q-0053 closed-negative @ R296 by CLM-0690
  # (RELATIVE-ROCOF-NO-GO).
  - id: Q-0053
    rank: 1
    phase: P1_residual_mechanism
    objective: >-
      Determine whether a strictly neighbour-local, zero-sum filtered
      relative-RoCoF residual directly changes the dominant differential
      active-power path and materially improves fast inter-area IAE without
      synchronization, common-frequency, or physical-constraint harm.
    required_reading:
      - memory/questions/Q-0053.md
      - memory/claims/CLM-0685.md
      - results/r295_consensus_timescale_probe/development_summary.json
      - src/andes_rl_kundur/control/decentralized_dapi.py
    verification:
      - Derive and seal two residual amplitudes before simulation.
      - Keep all non-treatment information, action, plant, and budget fields matched.
      - Require exact residual zero-sum and every completion/physical guard.
      - Use one 12-trajectory development screen only.
    scope_limits:
      - Fixed modified Kundur outcome-aware development cases only.
      - No full evaluation unless a candidate passes.
      - No neural, manuscript, architecture, topology, robustness, stability,
        safety, or deployment claim.
    stop_when:
      - A candidate passes and becomes eligible for disjoint held-out evaluation.
      - Both candidates fail and the structure closes negative.

  # Archived 2026-08-02: Q-0054 closed-positive @ R297 by CLM-0695
  # (RELATIVE-ROCOF-FULL-AMPLITUDE-CANDIDATE-IDENTIFIED).
  - id: Q-0054
    rank: 1
    phase: P1_residual_mechanism
    objective: >-
      Determine whether one full anchor-magnitude zero-sum relative-RoCoF
      residual passes the frozen development materiality and no-harm gates,
      ending gain revision regardless of direction.
    required_reading:
      - memory/questions/Q-0054.md
      - memory/claims/CLM-0690.md
      - results/r296_relative_rocof_probe/development_summary.json
      - src/andes_rl_kundur/control/relative_rocof_residual.py
    verification:
      - Freeze exactly baseline and one full-anchor arm.
      - Run eight matched development trajectories.
      - Retain all zero-sum, completion, common, synchronization, and physical guards.
      - Predeclare the separate held-out bank before outcomes.
    scope_limits:
      - Final development gain revision only.
      - No full evaluation unless the candidate passes.
      - No neural, manuscript, topology, architecture, stability, safety,
        robustness, or deployment claim.
    stop_when:
      - The candidate passes and a new round freezes the predeclared full bank.
      - The candidate fails and gain revision stops.

  # Archived 2026-08-02: Q-0055 closed-positive @ R298 by CLM-0700
  # (VALID-RELATIVE-ROCOF-PASS).
  - id: Q-0055
    rank: 1
    phase: P1_residual_mechanism
    objective: >-
      Determine whether the R297-selected explicit local zero-sum
      relative-RoCoF residual retains material fast inter-area improvement
      over fresh DAPI on the predeclared disjoint operating bank, and bound its
      executed-formulation relation to centralized vector PI.
    required_reading:
      - memory/questions/Q-0055.md
      - memory/claims/CLM-0695.md
      - results/r297_relative_rocof_amplitude/development_summary.json
      - src/andes_rl_kundur/control/relative_rocof_residual.py
    verification:
      - Use exactly the 12-case bank embedded in the R297 seal.
      - Freshly run baseline DAPI, selected residual DAPI, and centralized vector PI.
      - Require 36/36 valid records and exact zero-sum residual execution.
      - Report paired intervals, registered endpoints, failures, and physical guards.
    scope_limits:
      - Held-out operating conditions within one modified Kundur plant only.
      - Central comparisons remain executed-formulation contrasts.
      - No neural, MARL, topology, robustness, stability, safety, EMT-HIL, or deployment claim.
    stop_when:
      - The formal bank yields a valid bounded classification and publication gate.

  # Archived 2026-08-03: Q-0056 closed-negative @ R299 by CLM-0705
  # (CLASSICAL-RETUNE; adaptive edge allocation no-go).
  - id: Q-0056
    rank: 1
    phase: P1_residual_mechanism
    objective: >-
      Determine whether the R298 explicit local zero-sum residual-DAPI
      baseline leaves material state-dependent edge-allocation headroom beyond
      the best fixed edge-gain arm, and whether causal pairwise local signals
      contain enough information to justify a deployable distributed residual.
    required_reading:
      - memory/questions/Q-0056.md
      - memory/claims/CLM-0700.md
      - results/r298_relative_rocof_formal/formal_summary.json
      - src/andes_rl_kundur/control/relative_rocof_residual.py
    verification:
      - Use a prospectively sealed four-case sentinel before any larger probe.
      - Match plant, base controller, action coordinates, constraints, timing, and endpoint definitions across arms.
      - Separate best-fixed gain value, outcome-oracle allocation headroom, and causal local-information signal.
      - Require exact pre-projection zero sum, complete traces, and all registered physical guards before reading performance.
    scope_limits:
      - Development information-value diagnosis on one modified Kundur plant only.
      - Outcome oracle is non-deployable and cannot support controller efficacy.
      - No MARL, neural, pure-architecture, topology, stability, safety, robustness, EMT-HIL, or deployment claim.
    stop_when:
      - The sentinel classifies no gap, classical retuning, outcome-only gap, or locally signalled adaptive headroom.
      - No neural training or formal performance claim occurs inside R299.

  # Archived 2026-08-03: Q-0057 closed-positive @ R300 by CLM-0710
  # (VALID-2KV-PASS).
  - id: Q-0057
    rank: 1
    phase: P1_residual_mechanism
    objective: >-
      Determine whether the R299-selected fixed doubled relative-RoCoF gain
      retains material differential-frequency value over the fresh CLM-0700
      baseline on the prospectively frozen disjoint bank, and bound its named
      executed-formulation relation to centralized vector PI.
    required_reading:
      - memory/questions/Q-0057.md
      - memory/claims/CLM-0705.md
      - results/r299_edge_information_probe/development_summary.json
      - memory/rounds/R299/edge_information_seal_v2.json
      - src/andes_rl_kundur/control/edge_relative_rocof_residual.py
    verification:
      - Use exactly the 12-case bank embedded in the effective R299 seal.
      - Freshly run base Kv, selected fixed 2Kv, and centralized vector PI.
      - Require 36/36 valid records, paired intervals, exact zero sum, and all physical guards.
      - Preserve the executed-formulation ceiling for centralized comparisons.
    scope_limits:
      - Held-out operating conditions within one modified Kundur plant only.
      - Central comparisons do not identify architecture value.
      - No neural, MARL, topology, robustness, stability, safety, EMT-HIL, or deployment claim.
    stop_when:
      - The formal bank yields a valid bounded classification and publication gate.
      - Invalidity or a failed registered gate prevents all efficacy interpretation.

  # Archived 2026-08-03: Q-0058 closed-negative @ R301 by CLM-0715
  # (2KV-SUFFICIENT-NO-BLIND-ESCALATION).
  - id: Q-0058
    rank: 1
    phase: P1_residual_mechanism
    objective: >-
      Determine whether the implemented sampled neighbour relative-RoCoF
      residual admits a controller-level common/differential separation and a
      prospective gain-sufficiency or stability-margin rule beyond CLM-0710,
      without outcome-driven gain sweeps.
    required_reading:
      - memory/questions/Q-0058.md
      - memory/claims/CLM-0710.md
      - results/r300_fixed_2kv_formal/formal_summary.json
      - memory/rounds/R300/fixed_2kv_formal_seal.json
      - src/andes_rl_kundur/control/relative_rocof_residual.py
      - src/andes_rl_kundur/control/edge_relative_rocof_residual.py
      - src/andes_rl_kundur/control/decentralized_dapi.py
      - results/r294_model_validation/stage_a/records/16__fixed_lti_anchor.json
    verification:
      - Derive the exact graph common-mode kernel and differential-mode gains.
      - Derive the implemented discrete RoCoF filter transfer and test its dissipativity band.
      - Test a sampled augmented fixed-anchor model only as a small-signal diagnostic.
      - Run EVAL-v2 on the completed R300 records as diagnostic only, never as formal authority.
      - Authorize a new nonlinear probe only if the prospective model yields one identifiable candidate.
    scope_limits:
      - Controller-level separation is not nonlinear plant decoupling.
      - The R294 fixed-anchor matrix is local and its coarse LPV extension was rejected.
      - No MARL, neural, topology, delay, robustness, certified stability, safety, EMT-HIL, or deployment claim.
    stop_when:
      - The model yields either one prospective candidate and explicit nonlinear test gate or a justified no-further-gain decision.
      - No training or outcome-driven 3Kv/4Kv sweep occurs in R301.

  # Archived 2026-08-03: Q-0059 closed-partial @ R302 by CLM-0720
  # (EVAL-READY-TRAINING-BLOCKED).
  - id: Q-0059
    rank: 1
    phase: P1_residual_mechanism
    objective: >-
      Make EVAL-v2 architecture-aware for genuine vector distributed traces,
      then decide from R294--R301 evidence whether a named residual mechanism
      justifies neural distributed-agent training beyond fixed 2Kv.
    required_reading:
      - memory/questions/Q-0059.md
      - memory/claims/CLM-0710.md
      - memory/claims/CLM-0715.md
      - results/r300_fixed_2kv_formal/formal_summary.json
      - results/r301_relative_rocof_margin/analysis_summary.json
    verification:
      - Legacy scalar EVAL-v2 behavior remains unchanged.
      - Vector EVAL requires paired physical records, hashes, completion, storage and zero-sum action validity.
      - R300 replay is diagnostic only and does not replace its formal summary.
      - Training requires a named 2Kv failure mechanism and prospective comparator/action/information gate.
    scope_limits:
      - No ANDES simulation or neural training in R302.
      - No manuscript edit or architecture-wide efficacy claim.
      - No weakening of EVAL-v2 evidence-status or integrity guards.
    stop_when:
      - The vector profile passes positive records and rejects frozen negative fixtures.
      - R300 has a read-only EVAL-v2 scorecard with EXTERNAL_AUTHORITY_REQUIRED.
      - Training receives an explicit authorize-or-block verdict tied to current evidence.

  # Archived 2026-08-03: Q-0060 closed-positive @ R303 by CLM-0725
  # (COUPLING-CLASSICALLY-CLOSED).
  - id: Q-0060
    rank: 1
    phase: P1_residual_mechanism
    objective: >-
      Determine whether heterogeneous device power, ramp, and SOC headroom
      makes independent projection leak a pre-projection zero-sum differential
      residual into executed common power, and whether a deterministic
      headroom-aware edge allocator closes that failure before any learning.
    required_reading:
      - memory/questions/Q-0060.md
      - memory/claims/CLM-0710.md
      - memory/claims/CLM-0715.md
      - memory/claims/CLM-0720.md
      - results/r300_fixed_2kv_formal/formal_summary.json
      - results/r302_vector_eval_training_gate/analysis_summary.json
    verification:
      - Derive requested common and differential coordinates before projection.
      - Sweep only predeclared heterogeneous headroom patterns and verify power, ramp and SOC feasibility.
      - Measure executed common leakage and retained differential authority under fixed 2Kv.
      - Test one deterministic headroom-aware allocator before any neural method.
      - Use architecture-aware EVAL for any compatible completed trace replay while preserving external authority.
    scope_limits:
      - Start with algebraic and unit-level probes; run ANDES only if the mechanism survives them.
      - No neural training, manuscript edit, or architecture-wide efficacy claim.
      - Controller-interface zero sum is not hard nonlinear plant decoupling.
    stop_when:
      - Projection leakage is either rejected as negligible or reproduced against a prospective threshold.
      - The deterministic allocator either closes the failure or leaves a named local-information residual.
      - Any later training proposal has frozen observation, action, comparator and kill-gate contracts.
  # Archived 2026-08-03: Q-0063 closed-negative @ R307 by CLM-0745
  # (INVALID-STAGE1-EXECUTION).
  - id: Q-0063
    rank: 1
    phase: P1_residual_mechanism
    objective: >-
      Determine whether the physical-60-Hz model-first plant executes the
      frozen common and three-edge signed active-power probes across OP0--OP2
      with correct command, achieved-power, SOC, local-linearity, and measured
      common/differential coupling semantics.
    required_reading:
      - memory/questions/Q-0063.md
      - memory/claims/CLM-0740.md
      - paper/decoupling_marl_model_first/working/model_contract.md
      - src/andes_rl_kundur/env/andes/model_first_contract.py
      - src/andes_rl_kundur/env/andes/model_first_env.py
    verification:
      - Seal OP0--OP2 and exactly one zero plus paired common and edge pulse bank.
      - Require all Stage-0 execution guards, exact M/D readback, signed power and SOC, no limiter activation, and frozen local-linearity ceilings.
      - Report both common-to-differential and differential-to-common gains without a pass-by-smallness threshold.
      - Run EVAL-v2 on compatible edge traces as diagnostic only and retain EXTERNAL_AUTHORITY_REQUIRED.
    scope_limits:
      - One modified Kundur phasor-domain plant and development operating points only.
      - No predictor fitting, controller efficacy, MARL value, topology generalization, stability, safety, or deployment claim.
      - No optimization sweep or neural training in R307.
    stop_when:
      - Stage 1 yields PASS, authority/modeling NO-GO, or invalid execution with immutable provenance.
      - The working conference title receives only an evidence-coverage checkpoint.
