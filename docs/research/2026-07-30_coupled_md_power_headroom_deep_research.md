# Coupled \(M\)–\(D\) / active-power headroom after R291

**Cutoff:** 2026-07-30

**Scope:** bounded Deep Research update after the completed R291 trace diagnosis

**Research question:** Can a controller with the same uniform scalar virtual-inertia action break the observed RoCoF-versus-3–10 s recovery trade-off? If not, what is the minimum additional authority, and what stability-constrained learning architecture is justified?

## Executive decision

**R291 does not prove that every possible time-varying uniform-\(M\) policy must fail. It does show that another learned or hand-tuned gate over the same scalar action is not justified.** The missing falsification is a constrained deterministic finite-horizon oracle over the *same* \(M(t)\) bounds, slew, action budget, information pattern, plant, and two co-primary endpoints. If that oracle cannot find a feasible Pareto point that jointly clears the registered recovery and no-harm gates, the uniform-\(M\) action space—not the gate optimizer—should be closed.

The minimum staged authority extension is:

1. **add coordinated virtual damping \(D(t)\) first**, because the primary literature treats \(M\) and \(D\) as complementary: inertia chiefly arrests the initial rate of change, while damping suppresses overshoot/oscillation and accelerates recovery;
2. **add an independently constrained fast active-power residual \(P_{\mathrm{fast}}(t)\) only if \(M+D\) remains infeasible**, because damping reshapes power response but does not remove the need for dispatchable headroom and energy when the post-support recovery phase contains a real power deficit.

If learning later becomes warranted, the defensible architecture is a stabilizing deterministic base plus a projected, bounded neural residual—or a Neural-PI family with a common switching certificate—not direct RL over an unproven action space. This is a future, separately sealed research question. It is not a reason to reopen R291 or add experiments to the current ICEMS line.

## Evidence boundary

The labels below are deliberate:

- **Local formal evidence** means a statement reproduced from the sealed R291 contract, summary, report, or traces.
- **Literature support** means a conclusion explicitly supported by a cited primary paper.
- **Local inference** means a proposed interpretation or next gate; it is not a published theorem or a registered project claim.

R291 must remain narrowly interpreted. Earlier programme evidence established that the frozen slow BESS droop–PI layer has active-power restoration authority (R274), that a fixed 3 s common-\(M\) pulse has useful early transient effects (R275), and that later differential-\(q\) results have their own bounded or invalid formal status (R278–R279, R286–R287). Therefore, R291 is **a negative result for deterministic handoff of the same common scalar \(M\) action**, not a failure of the complete fast–slow framework, all active-power control, all RL, or all multi-agent control.

### Method and self-adversarial check

The search was frozen at 2026-07-30 and retained only primary peer-reviewed papers or authoritative author preprints, prioritizing 2023–2026. It was organized around the six prespecified axes and tested the counter-hypotheses that R291 was only a poor-gate result, that \(D\) adds no distinct authority, and that learning or MARL could help without action-space headroom. No primary source was found that standardizes a dual absolute-time/release-aligned metric protocol; that recommendation is therefore identified below as local inference rather than literature consensus.

## What the R291 traces actually say

Sources: [`handoff_contract.json`](../../results/r291_state_aware_handoff/handoff_contract.json), [`formal_summary.json`](../../results/r291_state_aware_handoff/formal_summary.json), the sealed [`traces`](../../results/r291_state_aware_handoff/traces), and the paper-facing [R291 feed](../../paper/icems2026/reports/R291.md).

| R291 fact | Evidence class | What it licenses | What it does **not** license |
|---|---|---|---|
| The fast action was uniform \(M\) only: \([1,1,1,1]\), \(\Delta M=+0.25\), \(\Delta D=0\), \(q=0\). The underlying \(D_{\mathrm{es}}=100\) remained fixed; “\(D=0\)” here means no adaptive damping action, not zero physical damping. | Local formal evidence | The test varied only a common inertia-like degree of freedom. | A conclusion about coordinated \(M+D\), differential allocation, or fast BESS power. |
| The tested common handoff improved 3–10 s IAE relative to fixed 3 s but worsened the secondary peak; relative to fixed 5 s it saved action but worsened secondary peak and mean maximum RoCoF. | Local formal evidence | The tested controller exposed an early-arrest / later-recovery trade-off. | A theorem that no \(M(t)\) waveform can break the trade-off. |
| Common \(M\) remained nonzero at the registered 3–10 s window start in 14/24 common-handoff scenarios. | Local trace diagnosis | The absolute 3 s analysis boundary did not coincide with effective support withdrawal in most of these cases. | Permission to discard the absolute-time endpoint post hoc. |
| The registered common “secondary peak” occurred at the 3–10 s window’s first sample in 17/24 common-handoff scenarios. | Local trace diagnosis | The endpoint often measured a boundary value, not a new interior post-release extremum. | A claim that the endpoint is invalid; it remains the sealed primary endpoint. |
| The common target gate switched more than once in 14/24 scenarios. | Local trace diagnosis | Repeated switching is material enough to retain switch/dwell/transition diagnostics. | A claim of Zeno behavior or high-frequency chatter; the controller already had hysteresis, dwell, and a 0.2 s update interval. |
| Full- and common-handoff action trajectories were identical in 23/24 scenarios. | Local trace diagnosis | Added differential/slow-gap observations had essentially no realized action information value under this rule. | A general conclusion that richer states or spatial control cannot help. |

The physical reading is straightforward but must remain an inference. A scalar \(M(t)\) changes the coefficient multiplying frequency acceleration; it can reshape RoCoF and timing, but it does not give an independent knob for oscillation damping or an independent dispatchable power command. The literature documents the same design tension: fixed inertia can trade maximum frequency deviation against settling time, while coordinated inertia and damping provide complementary transient roles [S1–S3]. That makes “optimize the same \(M\) once, then add \(D\), then add \(P_{\mathrm{fast}}\) only if needed” a sharper test than learning another gate.

## Axis 1 — coordinated adaptive virtual inertia and damping by transient phase

**Literature support.** Gurski et al. tune an adaptive-inertia/adaptive-damping VSG against maximum frequency deviation and settling time, evaluate 10,000 nonlinear initial conditions, and explicitly separate the role of adaptive inertia in early transients from adaptive damping in oscillation attenuation [S1]. Zhang et al. vary virtual inertia and damping between deviation and recovery phases in a virtual-oscillator-controlled inverter [S2]. Huang et al. identify the fixed-inertia contradiction between maximum frequency deviation and settling time and validate a nonlinear adaptive-inertia controller with a full-order small-signal model and HIL [S3]. Sati et al. add a virtual damping stabilizer to BESS inertia/damping loops and validate frequency/oscillation improvement using eigenvalue analysis, sensitivity studies, and OPAL-RT experiments [S4].

**Limits of that support.** These papers do not prove that the proposed strategies will dominate the R291 fixed-3 s benchmark on the modified Kundur V4 + separate ESD1 plant. Some use converter- or microgrid-level models and different objectives. Gurski et al. also state that adaptive VSG support still depends on a dispatchable power source [S1].

**Local inference.** \(D(t)\) is the minimum additional fast authority worth testing. It should be added as a bounded, slew-limited physical control channel and optimized jointly with \(M(t)\), not used as an unbounded numerical stabilizer. In this model family, \(D(1-\omega)\) entails an active-torque/power response; it is incorrect to describe \(D\) as energy-free. The authority contract must therefore freeze available power, converter/current capability, and the interpretation of the damping command.

## Axis 2 — bumpless/hybrid handoff, dwell, and repeated switching

**Literature support.** Feng et al. formulate variable-inertia frequency control as a nonlinear switching system. Their Neural-PI controllers share a Lyapunov structure, and the common Lyapunov function is invariant to controller changes, so controller switching retains exponential input-to-state stability under the paper’s assumptions [S5]. Lu et al. give a general interpolated bumpless-transfer construction for asynchronously switched linear systems [S6].

**Limits of that support.** Neither paper certifies the exact R291 supervisor, VSG proxy, ESD1 dynamics, saturation logic, or nonlinear ANDES trajectory. The bumpless-transfer paper is general switched-systems theory, not a power-system validation. R291 already used hysteresis, confirmation dwell, minimum on/off times, and a 1 s taper; therefore, “add hysteresis” alone is not a credible response to the 14/24 repeated switches.

**Local inference.** A future hybrid controller needs one of two explicit certificates:

- a common Lyapunov/ISS condition covering all \(M\), \(D\), and power-control modes and their interpolation, allowing arbitrary admissible switching; or
- mode-specific certificates plus a proven minimum/average dwell-time condition.

It must also use bumpless state initialization or continuous interpolation for controller internal states and for \(M\), \(D\), and \(P_{\mathrm{fast}}\); separately audit command discontinuity, physical power discontinuity, total variation, switch count, minimum inter-switch time, and dwell violations. These are verification obligations, not additional reward terms.

## Axis 3 — secondary frequency dip and fast/slow BESS takeover

**Literature support.** Boyle et al. show that abrupt transition from synthetic-inertia delivery to wind-turbine speed recovery can cause a secondary frequency dip, and coordinate wind and BESS active power to cover the recovery deficit while smoothing the transition [S7]. Xiong et al. divide wind–BESS frequency support into response and rotor-recovery stages; the BESS supplies supplementary power during recovery to prevent the secondary drop, with explicit SOC and charging/discharging constraints [S8]. Yan et al. model the power pit caused by DFIG speed recovery and trigger recovery at the first return to the primary-regulation quasi-steady frequency [S9].

**Limits of that support.** R291 has no wind-rotor recovery mechanism, and its “secondary peak” is an absolute-frequency metric over a fixed window. The cited work supports the *mechanism class*—withdrawal/recovery can expose an active-power deficit—not the claim that this specific mechanism caused every R291 boundary peak.

**Local inference.** If the constrained \(M+D\) oracle cannot jointly improve RoCoF and recovery, the next minimum authority is a fast BESS active-power residual around the frozen slow droop–PI command:

\[
P_{\mathrm{BESS}}^{\star}(t)
=P_{\mathrm{slow}}(t)+P_{\mathrm{fast}}(t),
\]

with prospectively frozen power, energy, SOC, headroom, efficiency, ramp/lag, current capability, and recharge/recovery contracts. The fast residual should cover the transition deficit and decay bumplessly as the slow layer takes over. It must not overwrite or retune the validated slow layer.

## Axis 4 — deterministic headroom before RL

The literature supplies both the method and the comparison standard:

- A two-layer multiple-model MPC sends constrained ESS virtual-inertia commands while accounting for SOC-dependent operation [S10].
- Sati et al. compare optimized \(M+D\), MPC-based \(M+D\), and a supplementary damping stabilizer [S4].
- Feng et al. use a finite-horizon LQR with complete model and inertia-trajectory information as an offline performance oracle, then train a real-time controller to imitate it [S11].

**Local inference: required oracle ladder.**

1. **Same-\(M\) oracle.** Solve a finite-horizon direct-transcription/MPC problem over the exact uniform scalar \(M_k\) action, with the R291 amplitude, slew, action-L1, causality, and hard-zero constraints. Produce the constrained Pareto frontier for RoCoF, 3–10 s IAE, boundary/interior secondary peak, physical safety, and effort. This is a falsification tool, not a deployable controller claim.
2. **\(M+D\) oracle.** Only if same-\(M\) lacks a feasible jointly acceptable point, add one coordinated \(D_k\) channel with a frozen physical authority contract. Re-solve the same frontier.
3. **\(M+D+P_{\mathrm{fast}}\) oracle.** Only if \(M+D\) remains infeasible, add a fast active-power residual with energy/SOC/headroom constraints.
4. **Implementability gap.** Compare clairvoyant finite-horizon, causal MPC, and a simple deterministic feedback approximation. A large clairvoyant–causal gap is an information problem; a small oracle gain is an authority problem. Neither should be mislabelled an RL problem.

The stop rule is falsifiable: **if the same-\(M\) oracle cannot clear the frozen joint endpoint and no-harm gates, no learned gate or direct RL may be trained on that action space.** If \(M+D\) or \(M+D+P_{\mathrm{fast}}\) cannot clear them either, stop the controller programme for this plant contract rather than widen the neural architecture.

## Axis 5 — safe residual or Neural-PI learning

**Literature support.** Feng et al. construct

\[
u_\psi(x)=Kx+\Pi[\pi_\psi(x)],
\]

where \(Kx\) is a stabilizing linear controller and the neural residual is projected onto a Lyapunov-decrease constraint. A common quadratic Lyapunov function certifies arbitrary switching among the modeled inertia modes; finite-horizon LQR trajectories provide the imitation target [S11]. Their later Neural-PI work provides exponential ISS for the nonlinear swing-equation modes and a common Lyapunov argument for switching among trained controllers [S5]. Yuan et al. constrain the neural-policy search space using Lyapunov stability and transient-frequency-safety conditions, with distributed dynamic budgets to reduce conservatism [S12].

**Limits of that support.** These are model-conditional guarantees. They do not transfer automatically through ANDES algebraic states, hybrid BESS logic, saturation, measurement delay, unmodeled topology, or the R261-affected historical checkpoints. The relevant certificate and projection must be derived and checked for the new plant/action contract.

**Local inference: justified learning form.**

- Keep the frozen classical slow controller and the best causal deterministic \(M+D\) or \(M+D+P_{\mathrm{fast}}\) controller as the base.
- Learn only a bounded residual inside independently enforced amplitude, slew, power, energy, SOC, and hybrid-transition constraints.
- Project the residual onto a verified Lyapunov/ISS condition where a tractable model supports it; otherwise use the neural policy only as a proposal behind a model-predictive safety filter and retain all filter interventions.
- Train from deterministic-oracle trajectories before any reward-only exploration.
- Require matched deterministic, centralized neural, and—only if spatial roles exist—distributed/shared comparisons on a fresh sealed bank.

Direct reward-only RL over \(M\), or a learned release gate over the existing \(M\) action, is not justified by either R291 or the cited safety literature.

## Axis 6 — absolute-time and release-aligned endpoints

The primary literature routinely defines physical phases relative to an event: synthetic-inertia delivery versus speed recovery [S7], staged wind–BESS response/recovery [S8], and recovery triggered at the first quasi-steady-frequency return [S9]. It therefore supports measuring phase-specific behavior. **This search did not find a primary paper establishing a standard dual-clock “absolute plus controller-release-aligned” endpoint protocol.** The following is a local measurement recommendation:

- retain the frozen disturbance-aligned endpoints (\(0\)–3 s, 3–10 s, and full horizon) for matched comparability and to avoid conditioning the headline result on a controller-selected release time;
- add per-trajectory release-aligned diagnostics using the *effective physical zero* of each fast channel, not “ready,” taper start, or release request;
- report, separately, the value at release, the first interior post-release extremum, its delay from release, post-release IAE over frozen horizons, and the fraction whose maximum occurs at the first sample;
- for \(M+D+P_{\mathrm{fast}}\), record distinct release/takeover times and power continuity for each channel;
- pair all release-aligned effects by scenario, retain failed/non-releasing cases, and treat absence of release as retained failure rather than missing data.

The 17/24 boundary-peak count is exactly why the boundary value and the interior post-release extremum should not be conflated. Release-aligned diagnostics explain mechanism; absolute-time endpoints retain falsifiability.

## Decision table

These decisions govern only a **future, newly authorized and prospectively sealed question**.

| Candidate | Decision | Falsifiable preconditions / gate |
|---|---|---|
| Same-\(M\) deterministic optimization | **GO** | One bounded oracle study only. Freeze the exact R291 uniform scalar action, amplitude/slew/L1/hard-zero constraints, plant, slow layer, bank protocol, and joint gates. **Pass:** a causal implementable approximation retains a feasible point jointly improving recovery without RoCoF/secondary-peak harm on sealed evaluation. **Fail/close action space:** even the finite-horizon oracle has no feasible jointly acceptable point. |
| \(M+D/P\) deterministic control | **CONDITIONAL** | Enter only after same-\(M\) headroom is absent or noncausal. Add \(D\) first with a physical power/capability contract; add \(P_{\mathrm{fast}}\) only if \(M+D\) remains infeasible. Each added channel must show incremental feasible Pareto headroom under matched constraints and sealed no-harm/energy/tail gates. |
| Safe residual neural controller / Neural-PI | **CONDITIONAL** | Enter only after a deterministic expanded-action controller demonstrates authority and a residual is needed to close a measured nonlinear/uncertainty gap. Require a stabilizing base, common-mode or dwell-time certificate, projection/safety filter, bounded residual, oracle imitation warm start, and sealed advantage over the deterministic base. |
| Direct RL or learned gate on the current scalar \(M\) action | **NO-GO** | Remains closed unless the same-\(M\) deterministic oracle first proves unused causal headroom and a learned policy clears stability, safety, effort, and fresh-bank advantage gates. More training, threshold search, reward shaping, or network width is not a substitute. |
| MARL | **NO-GO** | Remains closed while all devices receive the same scalar action and full/common trajectories are identical in 23/24 cases. Reconsider only if distinct local actions or resource constraints create a falsifiable allocation problem, observations have demonstrated information value, and a size-/information-matched centralized controller is the primary baseline. |

## Recommended next objective—if the programme is reopened

> **Falsifiable objective:** Under the frozen R291 plant, slow controller, disturbance generator, physical 60-Hz endpoints, and actuator limits, determine whether a constrained causal controller can jointly improve early RoCoF and post-support 3–10 s recovery relative to fixed 3 s; first exhaust the uniform-\(M\) action space with a deterministic finite-horizon oracle, then admit \(D\), and finally admit fast BESS active power only if the preceding action space is infeasible.

This objective separates three failure modes:

- **same-\(M\) oracle succeeds:** R291 was a controller-logic failure; learning is still optional, not automatic;
- **same-\(M\) fails but \(M+D\) succeeds:** missing damping authority caused the trade-off;
- **\(M+D\) fails but \(M+D+P_{\mathrm{fast}}\) succeeds:** the recovery phase required independent active-power/energy authority.

Only the third outcome justifies describing fast BESS takeover as necessary on this plant contract. None of these outcomes should be presumed from the literature.

## Primary sources

- **[S1]** E. Gurski, R. Kuiava, F. Perez, R. A. S. Benedito, and G. Damm, “A Novel VSG with Adaptive Virtual Inertia and Adaptive Damping Coefficient to Improve Transient Frequency Response of Microgrids,” *Energies*, 17(17), 4370, 2024. [doi:10.3390/en17174370](https://doi.org/10.3390/en17174370)
- **[S2]** W. Zhang et al., “Virtual Oscillator-Controlled Inverters with Adaptive Virtual Inertia and Damping to Support Frequency Stability,” *IECON 2024*. [doi:10.1109/IECON55916.2024.10905105](https://doi.org/10.1109/IECON55916.2024.10905105)
- **[S3]** R. Huang, C. Dong, Z. Wu, X. Quan, Z. Wang, T. Sun, and K. Hou, “A sigmoid-based adaptive inertia control strategy for grid-forming inverter to enhance frequency stability,” *Frontiers in Energy Research*, 11, 2023. [doi:10.3389/fenrg.2023.1095610](https://doi.org/10.3389/fenrg.2023.1095610)
- **[S4]** S. E. Sati, A. Al-Durra, H. Zeineldin, T. H. M. El-Fouly, and E. F. El-Saadany, “A novel virtual inertia-based damping stabilizer for frequency control enhancement for islanded microgrid,” *International Journal of Electrical Power & Energy Systems*, 155, 109580, 2024. [doi:10.1016/j.ijepes.2023.109580](https://doi.org/10.1016/j.ijepes.2023.109580)
- **[S5]** J. Feng, W. Cui, J. Cortés, and Y. Shi, “Online Event-Triggered Switching for Frequency Control in Power Grids With Variable Inertia,” *IEEE Transactions on Power Systems*, 40(4), 3347–3360, 2025. [doi:10.1109/TPWRS.2024.3523262](https://doi.org/10.1109/TPWRS.2024.3523262)
- **[S6]** S. Lu, T. Wu, L. Zhang, J. Yang, and Y. Liang, “Interpolated Bumpless Transfer Control for Asynchronously Switched Linear Systems,” *IEEE/CAA Journal of Automatica Sinica*, 11(7), 1579–1590, 2024. [doi:10.1109/JAS.2023.124155](https://doi.org/10.1109/JAS.2023.124155)
- **[S7]** J. Boyle, T. Littler, and A. M. Foley, “Coordination of synthetic inertia from wind turbines and battery energy storage systems to mitigate the impact of the synthetic inertia speed-recovery period,” *Renewable Energy*, 223, 120037, 2024. [doi:10.1016/j.renene.2024.120037](https://doi.org/10.1016/j.renene.2024.120037)
- **[S8]** L. Xiong et al., “Multi-objective distributed control of WT-PV-BESS integrated weak grid via finite time containment,” *International Journal of Electrical Power & Energy Systems*, 156, 109709, 2024. [doi:10.1016/j.ijepes.2023.109709](https://doi.org/10.1016/j.ijepes.2023.109709)
- **[S9]** X. Yan et al., “Recovery time and strategy of DFIG speed based on a high-proportional hydropower grid,” *Electric Power Systems Research*, 228, 110073, 2024. [doi:10.1016/j.epsr.2023.110073](https://doi.org/10.1016/j.epsr.2023.110073)
- **[S10]** “A novel virtual inertia control strategy for frequency regulation of islanded microgrid using two-layer multiple model predictive control,” *Applied Energy*, 343, 121233, 2023. [doi:10.1016/j.apenergy.2023.121233](https://doi.org/10.1016/j.apenergy.2023.121233)
- **[S11]** J. Feng, M. Muralidharan, R. Henriquez-Auba, P. Hidalgo-Gonzalez, and Y. Shi, “Stability-Constrained Learning for Frequency Regulation in Power Grids With Variable Inertia,” *IEEE Control Systems Letters*, 8, 994–999, 2024. [doi:10.1109/LCSYS.2024.3408068](https://doi.org/10.1109/LCSYS.2024.3408068)
- **[S12]** Z. Yuan, C. Zhao, and J. Cortés, “Reinforcement learning for distributed transient frequency control with stability and safety guarantees,” *Systems & Control Letters*, 185, 105753, 2024. [doi:10.1016/j.sysconle.2024.105753](https://doi.org/10.1016/j.sysconle.2024.105753)
