# RL–VSG algorithm, evaluation, and publication landscape (2026-07-24)

## Executive verdict

This note answers a narrow question: **given the current `andes-rl-kundur`
evidence, what would count as a genuinely better algorithm, are the paper and
project metrics scientifically adequate, and what publication level is
realistic?**

The strict answer is:

1. **The current repository has not yet demonstrated a generally better
   algorithm.** It has demonstrated a useful Pareto trade-off on one modified
   Kundur benchmark: the legacy recurrent controller is better on the project's
   11-axis score, while droop is better on the paper's global synchronization
   reward. Neither dominates.
2. **The paper metric is valid but incomplete.** It measures inter-VSG frequency
   coherence, not restoration to nominal frequency. It can assign the best
   possible score when all buses drift together.
3. **The 11-axis score is useful as a diagnostic paper-alignment dashboard but
   is not yet a validated control-quality objective.** Several axes measure
   closeness to visually extracted paper traces or reward action utilisation,
   not monotonic physical improvement.
4. **Changing TD3/SAC/PPO or adding LSTM is no longer a sufficient contribution
   by itself.** Recent work already includes TD3 with RTDS validation, safe RL
   with a Lyapunov/region-of-attraction argument, decentralized PPO multi-VSG
   control in PSCAD, and topology-aware GNN–RL.
5. The most defensible next contribution is a **physics- and safety-constrained,
   topology-aware residual controller**:

   \[
   u_t = u_{\mathrm{droop}}(x_t)
       + g_\theta(x_t,G)\,\Delta u_\theta(x_{0:t},G),
   \]

   with graph message passing, a temporal encoder, explicit feasible projection
   of inertia/damping commands, and a pre-registered multi-objective evaluation.
   The research claim must be cross-topology/OOD generalisation or a physical
   mechanism—not merely “GNN improves score”.

Publication assessment is therefore conditional:

| Evidence package | Realistic status / venue band |
|---|---|
| Repository as-is | **Not submission-ready as an algorithm paper.** At most a technical report, workshop/conference replication, or a carefully reframed negative/reproducibility study after cleaning the evidence. |
| Corrected recurrent algorithm, one topology, robust seeds and held-out disturbances | Plausible for **IEEE Access, IET Generation, Transmission & Distribution, or Electric Power Systems Research** if the method is clear and the evaluation is statistically credible. |
| Physics/safety-informed graph residual, multiple systems and sealed topology-OOD tests | Plausible for **IJEPES, Sustainable Energy, Grids and Networks, or Journal of Modern Power Systems and Clean Energy**; stronger than a single-system algorithm comparison. |
| Above plus stability/safety result, cross-simulator or HIL/RTDS evidence, and system-level insight of lasting value | A credible attempt at **IEEE Transactions on Power Systems**; **IEEE Transactions on Smart Grid** only when framed around microgrids/active distribution networks and communications, which are explicitly in its scope. |

These are research-readiness bands, not acceptance predictions or official
journal rankings.

## 1. What the source paper actually evaluates

The source is Yang et al., “A Distributed Dynamic Inertia-Droop Control
Strategy Based on Multi-Agent Deep Reinforcement Learning for Multiple
Paralleled VSGs,” *IEEE Transactions on Power Systems*, 38(6), 5598–5612,
2023, DOI [10.1109/TPWRS.2022.3221439](https://doi.org/10.1109/TPWRS.2022.3221439).

Its global test reward is

\[
C_{\mathrm{sync}}
=-\sum_{e=1}^{E}\sum_{t=1}^{M}\sum_{i=1}^{N}
  \left(f_{i,e,t}-\bar f_{e,t}\right)^2,\qquad
\bar f_{e,t}=\frac{1}{N}\sum_i f_{i,e,t}.
\]

For the main experiment, \(N=4\), \(M=50\), the control interval is 0.2 s,
and 50 random test episodes are accumulated without normalising by episode,
time step, or agent count. The paper reports DDIC −8.04, adaptive inertia
−12.93, and no control −15.2. The main physical platform is a modified Kundur
two-area system with four storage VSGs. It uses 100 randomly generated training
cases and 50 randomly generated test cases, plus communication-failure and
0.2 s-delay tests. The full paper also extends beyond the four-agent main case
to weak-grid/scaling and New England 39-bus/fault experiments. The repository's
canonical paper fact sheet records the transcribed settings and unresolved
ambiguities in [the local source audit](../paper/kd_4agent_paper_facts.md).

### What `cum_rf` does and does not establish

`cum_rf` is scientifically meaningful for **differential/inter-area
synchronisation**: it penalises frequency dispersion among VSG buses. It is
also closely tied to the source paper's stated power-oscillation mechanism.

It is insufficient as a sole frequency-control metric because:

- if \(f_i(t)=f_j(t)\) for every pair but all nodes are far from nominal,
  \(C_{\mathrm{sync}}=0\), its optimum;
- it does not directly constrain nadir/zenith, RoCoF, steady-state frequency
  error, settling time, damping ratio, control energy, saturation, or safety
  violations;
- its magnitude changes with episode count, horizon, sample interval, number
  of agents, and frequency-unit basis, so absolute values are not comparable
  across systems without normalisation;
- accumulated reward can conceal tail failures unless failure rate and
  worst-case/CVaR statistics are also reported.

This is not just a methodological preference. Operational frequency studies
use multiple characteristics. ENTSO-E's frequency-stability material explicitly
discusses frequency nadir and admissible RoCoF, while a NERC study tabulates
nadir, RoCoF, settling frequency and damping-related results
([ENTSO-E frequency stability evaluation](https://www.entsoe.eu/Documents/SOC%20documents/RGCE_SPD_frequency_stability_criteria_v10.pdf);
[NERC EV study](https://www.nerc.com/globalassets/who-we-are/standing-committees/rstc/evstudyreport.pdf)).
Recent VSG-RL papers likewise use bounded frequency deviation, RoCoF and
settling time rather than cumulative reward alone.

**Recommendation:** retain a normalised version of `cum_rf` as the
“differential-mode synchronisation” endpoint, but never call it overall
frequency quality.

## 2. Assessment of the project's 11-axis score

The implementation in
[`paper_grade_axes.py`](../../src/andes_rl_kundur/evaluation/paper_grade_axes.py)
combines:

- peak and final frequency deviation, settling time;
- inertia/damping smoothness and action-range utilisation;
- improvement against no control;
- gates for minimum per-agent activity, late oscillation, and active-power
  balance.

This is much richer than `cum_rf` and has been valuable for discovering
degenerate “all agents drift together” policies. However, its current semantics
are closer to a **paper-figure-alignment score** than a validated multi-objective
control-performance index:

1. Several continuous axes use a symmetric distance from a paper trace target.
   A controller materially better than the paper target can therefore score
   worse simply because it is less similar.
2. Inertia/damping “utilisation” rewards using a larger fraction of the paper
   action range. This is not equivalent to minimum control effort and can reward
   unnecessary actuation.
3. `agent_min_activity` assumes every agent should act; sparse optimal control
   could be penalised.
4. Equal active-power sharing is not automatically optimal when VSG capacities,
   locations, headroom, or disturbance sensitivities differ.
5. Tolerances and gating thresholds are engineering judgements, and the
   geometric-mean/min aggregation encodes an implicit utility function.
6. The metric evolved across versions. Unless one frozen version is
   pre-registered, retrospective algorithm search creates evaluator overfitting.

**Recommendation:** keep the 11 axes as a dashboard, but replace `geo` as the
primary scientific endpoint with:

- primary physical outcomes: nadir/zenith, worst-bus and COI frequency,
  RoCoF, settling time, IAE/ITAE, inter-VSG dispersion, and oscillatory-mode
  damping;
- operational costs: \(\int |u|dt\), \(\int u^2dt\), action total variation,
  saturation duration, energy/headroom use;
- hard outcomes: instability/TDS failure, constraint violation, protection
  threshold crossing;
- multi-objective reporting: Pareto fronts, hypervolume, and a single
  pre-declared engineering operating point.

Before using `geo` in a paper, run threshold sensitivity, leave-one-axis-out
rank stability, monotonicity tests, and correlation with independent physical
outcomes. Rename it “paper-alignment composite” rather than “overall score”.

## 3. 2022–2026 research frontier

The progression of peer-reviewed work makes the novelty bar clear:

| Work | Main advance | Evaluation signal |
|---|---|---|
| 2022, DDPG VSG self-tuning, *Energy Reports* | Single-machine DDPG tuning of inertia/damping | MATLAB/Simulink; settling response 0.448 s versus 0.632/0.818 s ([publisher paper](https://doi.org/10.1016/j.egyr.2022.02.147)) |
| 2023, Yang et al., *TPWRS* | Distributed multi-agent SAC for dynamic inertia/droop distribution; analytical oscillation motivation | Modified Kundur, random train/test cases, communication failure/delay, additional scaling/system tests ([DOI](https://doi.org/10.1109/TPWRS.2022.3221439)) |
| 2023/24, Oboreh-Snapps et al., *IEEE TEC* | TD3, settling-time state, simultaneous frequency/RoCoF/settling targets | MATLAB/Simulink **and RTDS**, compared with adaptive tuning methods ([author-institution record](https://scholarsmine.mst.edu/ele_comeng_facwork/5088/), [DOI](https://doi.org/10.1109/TEC.2023.3309955)) |
| 2024, Benhmidouch et al., *EPSR* | Small-signal stability bounds; TD3 compared with DDPG and SAC; redesigned state/reward | Nadir, RoCoF, training time/reward and non-adaptive VSG comparison ([publisher paper](https://doi.org/10.1016/j.epsr.2024.110269)) |
| 2025, Shuai et al., *JMPCE* | Safe model-based RL combining GP dynamics, ADP and Lyapunov region of attraction | Droop/DDPG/SAC, increasing disturbances and ±30% inertia/damping uncertainty ([open paper](https://doi.org/10.35833/MPCE.2023.000882)) |
| 2025, Kang et al., *IJEPES* | Decentralised multi-VSG PPO with shared reward and constrained learning | PSCAD IEEE 33-bus; load variation, islanding and faults ([publisher paper](https://doi.org/10.1016/j.ijepes.2025.111374)) |
| 2026, physics/sensitivity-informed GNN–RL, *SEGAN* | Spectral-sensitivity virtual-inertia allocation embedded in topology-aware spatio-temporal GNN–RL | Contingency/topology-aware transmission-grid study ([publisher paper](https://doi.org/10.1016/j.segan.2026.102168)) |

The table does not claim every paper has ideal statistics; it establishes the
**current contribution bar**. A new LSTM/TD3 variant evaluated only on LS1/LS2
is weaker than already published safety, PSCAD/RTDS, and topology-aware work.

### Defensible research gap

“Apply GNN to VSG control” is no longer empty. A narrower gap remains:

> distributed multi-VSG dynamic inertia/damping control that separates
> common- and differential-frequency modes; uses a droop prior plus learned
> residual/gate; enforces physical stability/action constraints; and
> demonstrates statistically reliable zero-/few-shot transfer across unseen
> network topology, VSG count, disturbance location and communication graph.

The project is unusually well placed to study the **metric conflict** itself:
paper sync reward can reward common-mode drift, while a physically anchored
objective prevents it. That is publishable only if formulated prospectively,
validated outside the discovery scenarios, and connected to a control
mechanism—not presented as a post-hoc score story.

## 4. Minimum credible experiment design

General RL methodology warns that point estimates from a few runs can reverse
conclusions. Henderson et al. show that non-determinism and implementation
details make unstandardised comparisons unreliable
([AAAI paper](https://doi.org/10.1609/aaai.v32i1.11694)). Agarwal et al.
recommend interval estimates, performance profiles and robust aggregates such
as IQM in few-run settings
([NeurIPS paper](https://proceedings.neurips.cc/paper/2021/hash/f514cec81cb148559cf475e7426eed5e-Abstract.html)).
Patterson et al. cover variation, stability, multiple-agent comparisons,
baselines, hyperparameters and experimenter bias
([JMLR paper](https://www.jmlr.org/papers/v25/23-0183.html)).

For this project:

### Splits and seeds

- Separate **training**, **model-selection/validation**, and sealed **test**
  distributions. LS1/LS2 may be illustrative plots, not the entire test set.
- Use paired common scenario seeds for every controller.
- Target at least 10 independent training seeds for the headline comparison
  when affordable; 5 is exploratory, not strong evidence. Evaluate each trained
  policy on a large fixed held-out scenario bank.
- Report all seeds, not the best checkpoint/seed. Pre-declare checkpoint
  selection.
- Report median, IQM, 95% stratified/bootstrap confidence intervals,
  probability of improvement, performance profiles, failure rate and
  worst-case/CVaR.

### Scenario and topology coverage

Hold out combinations of:

- load size, sign, bus, onset time and multi-event disturbances;
- renewable penetration and generator/VSG inertia/damping;
- communication delay, dropout, packet corruption and graph changes;
- line/generator outage, faults and fault-clearing times;
- unseen VSG counts and unseen network topologies.

For a topology-generalisation claim, train on multiple networks/topology
variants and test on **entirely unseen** graphs. A line outage within the same
fixed Kundur graph is robustness evidence, not broad cross-system
generalisation.

### Baselines and ablations

Use identical observations, action bounds, interaction budgets, simulator
settings and tuning budgets for:

- no control and fixed VSG;
- tuned droop and non-learning adaptive inertia/droop;
- PI/MPC or another credible model-based controller;
- source-paper SAC/DDIC;
- strong TD3, SAC and PPO baselines;
- the corrected recurrent controller;
- proposed graph/residual/safety method.

Required ablations: MLP versus GNN, recurrent versus memoryless, pure RL versus
droop residual/gating, constraint projection on/off, and each reward/objective
component. Do not compare a tuned proposed method with untuned default
baselines.

### Fidelity

- Retrain all recurrent policies after the Bellman-target fix.
- Choose one nominal-frequency basis and rebaseline all absolute-Hz metrics.
- Validate at least one conclusion in another simulator or in
  controller-/power-hardware-in-the-loop for a high-tier claim.
- Publish configs, raw per-seed results, failure traces and code.

## 5. Three publication-readiness bands

### A. Current repository, as-is

The current evidence includes a useful dual-metric Pareto result
([R252](../../memory/rounds/R252/verdict.md),
[R262](../../memory/rounds/R262/verdict.md)), but:

- R201 and related recurrent checkpoints were trained with the legacy
  misaligned recurrent Bellman target; corrected-algorithm performance is
  untested ([R261](../../memory/rounds/R261/verdict.md));
- the canonical evidence is seed-42, fixed LS1/LS2, with no sealed topology
  hold-out;
- historical absolute-frequency fields use the legacy 50 Hz control basis while
  the ANDES case is physically 60 Hz
  ([ADR-0006](../adr/0006-dual-frequency-reporting-preserve-v4.md));
- no algorithm dominates both `geo` and `cum_rf`;
- the simulator/topology/reward/action bounds differ materially from the source
  paper.

**Verdict:** do not submit this as “a superior algorithm”. A transparent
replication/negative-results contribution is possible after consolidation,
because IEEE Access explicitly accepts applied engineering and negative
results, but the current correctness boundary must first be resolved
([IEEE Access scope](https://ieeeaccess.ieee.org/about/)).

### B. Corrected algorithm, still one topology

After corrected retraining, multi-seed statistics, a sealed disturbance bank,
fair baselines/ablations, and a frozen metric protocol, a strong single-system
paper could fit:

- [Electric Power Systems Research](https://www.sciencedirect.com/journal/electric-power-systems-research)
  — broad systems studies including control, optimisation and stability;
- [IET Generation, Transmission & Distribution](https://ietresearch.onlinelibrary.wiley.com/hub/journal/17518695/homepage/productinformation.html)
  — power-system operation/control, modelling and computational intelligence;
- [IEEE Access](https://ieeeaccess.ieee.org/about/)
  — broad, technically sound applied engineering, including negative results.

IJEPES is possible only if the algorithmic/mechanistic contribution is strong
and the validation substantially exceeds two scenarios, because its official
scope emphasises new technologies and performance in systems of varied size
and complexity
([IJEPES guide](https://www.sciencedirect.com/journal/international-journal-of-electrical-power-and-energy-systems/publish/guide-for-authors)).

### C. Cross-topology graph/residual algorithm

With multi-system topology-OOD evaluation, physical constraint enforcement and
clear mechanism ablations, realistic targets include:

- [IJEPES](https://www.sciencedirect.com/journal/international-journal-of-electrical-power-and-energy-systems/publish/guide-for-authors);
- [Sustainable Energy, Grids and Networks](https://www.sciencedirect.com/journal/sustainable-energy-grids-and-networks),
  whose scope explicitly welcomes fundamental computational methods applied to
  power/energy and information-coupled grids;
- *Journal of Modern Power Systems and Clean Energy*.

For [IEEE Transactions on Power Systems](https://ieee-pes.org/publications/transactions-on-power-systems/),
the paper must deliver lasting system-level insight in power-system dynamic
performance, stability or control—not only an architecture change. A credible
package would add a stability/safety result, strong OOD topology evidence,
cross-simulator/HIL validation, and reproducible statistics.

[IEEE Transactions on Smart Grid](https://ieee-pes.org/publications/transactions-on-smart-grid/)
is a fit only if the study is recast around microgrids or active distribution
networks with DER/communication interaction. Its official page explicitly lists
transmission-system renewable-energy work as out of scope.

IEEE *Transactions on Energy Conversion* is not the natural target for the
present phasor-domain ANDES study: its official scope says power electronics
and control should not be the primary contribution unless embedded in the
energy-conversion apparatus
([TEC scope](https://ieee-pes.org/publications/transactions-on-energy-conversion/)).
It becomes plausible only with converter/device-level and RTDS/HIL evidence.

## 6. Recommended next algorithm programme

1. **Repair the evidence base first.** Retrain corrected TD3-LSTM and
   memoryless TD3/SAC baselines under one frozen environment, physical
   frequency basis and held-out scenario bank. This is a prerequisite, not the
   novelty.
2. **Decompose the control goal.** Use a common-mode objective for nominal
   frequency restoration and a differential-mode objective for inter-VSG
   synchronisation. Treat energy, action variation and parameter conservation
   as costs/constraints.
3. **Use droop as a stabilising prior.** Learn only a bounded residual and
   state-dependent gate. This directly tests the mechanism suggested by the
   observed droop/RL Pareto front.
4. **Add graph and temporal structure only for a testable reason.** Shared
   message-passing weights should enable variable VSG count/topology; a
   GRU/LSTM should address partial observability and delay. Compare each against
   matched MLP/memoryless ablations.
5. **Project actions into a safe set.** Derive admissible inertia/damping
   regions from small-signal or Lyapunov analysis; report violations and
   region-of-attraction/robustness evidence.
6. **Optimise a vector/constrained objective.** Do not directly optimise the
   heuristic `geo`. Select the published operating point before opening the
   sealed test set.
7. **Earn the publication tier with validation.** Single Kundur establishes
   feasibility; unseen IEEE 39/118 or active-distribution graphs establish
   generalisation; cross-simulator or HIL/RTDS establishes practical
   credibility.

The key decision is therefore not “which RL algorithm next?” It is whether the
project will become a **single-benchmark optimisation study** or a
**mechanism-driven, safe, topology-generalising control study**. Only the latter
has a credible path to the top specialist power-system journals in the current
literature landscape.

## Sources checked

Primary/first-party sources used above:

- Yang et al. source paper DOI:
  <https://doi.org/10.1109/TPWRS.2022.3221439>
- Oboreh-Snapps et al. institutional record and definitive DOI:
  <https://scholarsmine.mst.edu/ele_comeng_facwork/5088/>,
  <https://doi.org/10.1109/TEC.2023.3309955>
- Benhmidouch et al., EPSR:
  <https://doi.org/10.1016/j.epsr.2024.110269>
- Shuai et al., safe RL:
  <https://doi.org/10.35833/MPCE.2023.000882>
- Kang et al., IJEPES:
  <https://doi.org/10.1016/j.ijepes.2025.111374>
- Physics/sensitivity-informed GNN–RL:
  <https://doi.org/10.1016/j.segan.2026.102168>
- RL evaluation methodology:
  <https://doi.org/10.1609/aaai.v32i1.11694>,
  <https://proceedings.neurips.cc/paper/2021/hash/f514cec81cb148559cf475e7426eed5e-Abstract.html>,
  <https://www.jmlr.org/papers/v25/23-0183.html>
- Journal official scopes:
  <https://ieee-pes.org/publications/transactions-on-power-systems/>,
  <https://ieee-pes.org/publications/transactions-on-smart-grid/>,
  <https://ieee-pes.org/publications/transactions-on-energy-conversion/>,
  <https://www.sciencedirect.com/journal/international-journal-of-electrical-power-and-energy-systems/publish/guide-for-authors>,
  <https://www.sciencedirect.com/journal/electric-power-systems-research>,
  <https://www.sciencedirect.com/journal/sustainable-energy-grids-and-networks>,
  <https://ietresearch.onlinelibrary.wiley.com/hub/journal/17518695/homepage/productinformation.html>,
  <https://ieeeaccess.ieee.org/about/>.

The source paper's exact equations and experiment details were cross-checked
against the repository's maintained PDF transcription. The 2025 IJEPES and
2026 SEGAN details available to this audit were publisher metadata/abstract and
highlights; claims beyond those first-party fields were intentionally not made.
