# Model-first coupled distributed control for the modified Kundur plant

**Date:** 2026-08-02
**Round/question:** R294 / Q-0051
**Scope:** primary-source model selection and prospective validation design;
no controller simulation or neural training.

## Decision

No single reduced model can honestly be called globally "most suitable" for
this problem.  The defensible choice is a three-level model stack:

1. the full nonlinear ANDES DAE is the plant-of-record and validation truth;
2. equilibrium descriptor-LTI/modal models identify modes, participation,
   observability, and actuator placement/authority;
3. a trajectory-linearized descriptor-LTV/LPV reduction is the leading online
   model for robust centralized and neighbour-distributed MPC.

A reduced nonlinear DAE/NMPC remains the fallback and offline upper reference
if LPV errors or mode-branch changes are too large.  Port-Hamiltonian,
passivity, or dissipativity arguments should supply a terminal/safety
condition where the plant abstraction supports them, rather than replace the
finite-horizon constrained controller.  Neural models enter only after this
stack and a deterministic controller pass a non-learning validation gate.

The controller cannot "fully solve coupling."  Common/differential
coordinates expose useful structure, but heterogeneous devices, electrical
network asymmetry, governors/AVRs, voltage dynamics, saturation, SOC, and
active-power limits generally leave nonzero cross-coupling.  The scientific
task is to measure and control that coupling, not delete it by assumption.

## 1. Exact plant boundary

The current project plant is a phasor-domain modified Kundur system containing
synchronous machines with governors and exciters, four `PV+GENCLS` VSG
proxies, and four separate grid-following `ESD1` storage devices.  The control
channels are therefore not a single physical unified GFM-BESS:

- `GENCLS.M` schedules a mass/time-constant parameter;
- `GENCLS.D` schedules proportional speed-error torque;
- `ESD1.paux` supplies an additive active-power command through current lag,
  current/power limits, efficiency, and SOC dynamics;
- PQ load changes are disturbances, not controlled demand.

The full plant is a semi-explicit nonlinear DAE

\[
E(\rho)\dot x=F(x,y,\rho,u_P,d),\qquad
0=G(x,y,d),
\]

where \(x\) contains dynamic machine, controller, VSG, storage-current, and
SOC states; \(y\) contains network voltage/angle and other algebraic states;
\(\rho=(M,D)\); \(u_P\) is BESS active power; and \(d\) is the load/network
disturbance.  This follows the ANDES DAE formulation, in which differential
and algebraic equations are solved together and linearization is obtained
from their Jacobians ([ANDES DAE formulation](https://docs.andes.app/en/latest/modeling/concepts/dae-formulation.html)).

For the VSG-frequency core,

\[
\dot\delta_i=2\pi f_n\Delta\omega_i,
\]

\[
(M_{0i}+u_{M,i})\dot{\Delta\omega_i}
=P_{m,i}-P_{e,i}
-(D_{0i}+u_{D,i})\Delta\omega_i+u_{P,i}.
\]

The separate ESD1 path adds active-current lag, voltage/current capability,
power projection, and SOC dynamics.  Any control model that omits those
states must bound the resulting prediction error and may not claim unified
converter-level GFM-BESS control.

## 2. Why inertia and damping are not ordinary LTI inputs

For inertia inside the descriptor/mass matrix,

\[
E(u_M)\dot x=F(x,y,u_D,u_P,d).
\]

Along a nominal trajectory, the inertia perturbation enters as

\[
B_M(t)\,\delta u_M
=-E^{-1}\frac{\partial E}{\partial u_M}
\dot x^\star(t)\,\delta u_M.
\]

At an equilibrium, \(\dot x^\star=0\), so this is not a conventional nonzero
additive input matrix.  Similarly, damping modulation has trajectory-dependent
authority proportional to frequency deviation.  Both channels can move
eigenvalues when treated as parameters, but ordinary equilibrium LQR that
inserts \(\Delta M\) as an arbitrary \(Bu\) is structurally misleading.

Active power, by contrast, is a direct input with energy, current, SOC, ramp,
and headroom constraints.  The project should therefore not pre-select
differential inertia.  It must compare modal and trajectory authority of
\(u_P,u_D,u_M\).  Primary work on inertia placement also shows that location,
not only total inertia, changes coherence and inter-area behavior
([Poolla et al.](https://doi.org/10.1109/TAC.2017.2703302),
[Pulgar-Painemal et al.](https://doi.org/10.1109/TPWRS.2017.2688921)).

## 3. Common/differential coordinates without false decoupling

Let

\[
\omega_c=\frac{\mathbf1^\top M_0\omega}
{\mathbf1^\top M_0\mathbf1},
\qquad z=T\omega,\qquad T\mathbf1=0,
\]

with an orthonormal differential basis \(T\).  The transformed model generally
has the form

\[
\begin{bmatrix}\dot x_c\\\dot x_d\end{bmatrix}
=
\begin{bmatrix}A_{cc}&A_{cd}\\A_{dc}&A_{dd}\end{bmatrix}
\begin{bmatrix}x_c\\x_d\end{bmatrix}
+
\begin{bmatrix}B_{cc}&B_{cd}\\B_{dc}&B_{dd}\end{bmatrix}
\begin{bmatrix}u_c\\u_d\end{bmatrix}+Ed.
\]

Zero-sum differential action does not imply \(A_{cd}=A_{dc}=0\), and a
coordinate change does not prove nonlinear or constrained output decoupling.
The validation must estimate cross transfers

\[
\gamma_{c\leftarrow d}=\|G_{c\leftarrow d}\|,
\qquad
\gamma_{d\leftarrow c}=\|G_{d\leftarrow c}\|,
\]

over the declared operating domain.  Small bounded gains justify a hierarchy;
large or strongly state-dependent gains require the predictive controller to
retain the cross blocks.  A fixed three-second switch is not a consequence of
this decomposition; time-scale separation must be measured from modes and
input/output response.

## 4. Candidate model and controller families

| Family | Strength | Limitation | R294 role |
|---|---|---|---|
| Equilibrium descriptor-LTI/modal | Directly supports eigenvalues, damping, participation, modal controllability, and model reduction | Local to an operating point; weak for saturation, SOC, and trajectory-dependent \(M,D\) actions | Mandatory analysis model, not final online controller |
| Trajectory descriptor-LTV/LPV | Retains scheduling dependence while permitting repeated QP-based constrained control | Needs scheduling-state estimation, a validity domain, and robust error bounds | Leading online model if validation passes; real-time/HIL precedent exists ([Hamilton et al.](https://doi.org/10.1109/TIA.2023.3304621)) |
| Robust/cooperative distributed MPC | Explicit local constraints, neighbour coordination, uncertainty sets, and receding-horizon handoff | Communication, convergence, recursive feasibility, and runtime must be measured | Leading deterministic distributed controller ([Ademola-Idowu and Zhang](https://doi.org/10.1109/TPWRS.2020.3019998); [robust DMPC](https://doi.org/10.1016/j.conengprac.2016.08.007)) |
| Reduced nonlinear DAE/NMPC | Best representation of large-signal coupling and nonlinear constraints | Nonconvex, costly, and difficult to certify or distribute | Offline upper reference or fallback if LPV is rejected ([Samanta et al.](https://doi.org/10.1109/TPWRD.2023.3336868)) |
| Nonlinear DAE consensus/ADMM | Closest distributed optimization to the full plant | Published implementations do not establish a universal convergence/stability guarantee | Research fallback, not first controller ([Goebel et al.](https://doi.org/10.1002/oca.3083)) |
| Port-Hamiltonian/passivity/DAPI | Gives physical energy structure and distributed stability conditions under stated assumptions | Does not by itself optimize finite-horizon RoCoF, nadir, SOC, and saturation trade-offs | Terminal/safety layer ([Arghir et al.](https://doi.org/10.1016/j.automatica.2018.05.037); [Schiffer and Doerfler](https://doi.org/10.1109/ECC.2016.7810500)) |
| GNN, DeePC, neural dynamics | Can exploit local graph messages or learn model discrepancy | Graph choice may not match influence structure; high-order data methods face scaling and coverage limits | Residual/approximation only after deterministic gates ([Lee et al.](https://doi.org/10.1016/j.apenergy.2022.119530); [Huang et al.](https://doi.org/10.1109/CDC40024.2019.9029522)) |

The provisional controller is therefore

\[
u_i=\Pi_{\mathcal U_i(x)}\left[
u_{i,\mathrm{DMPC}}
+r_\theta\!\left(o_i,
\{m_{j\rightarrow i}\}_{j\in\mathcal N_i}\right)
\right],
\]

but R294 authorizes only the deterministic/modeling part.  Common-frequency
restoration is led by energy-feasible BESS active-power frequency shaping or
MPC; differential/inter-area behavior is handled by neighbour-cooperative
LPV-DMPC; \(M,D\) enter only after authority screening.  Frequency-shaping
work supports directly designing BESS power response rather than assuming a
virtual-inertia imitation is optimal
([Jiang et al.](https://doi.org/10.1109/TAC.2020.3034198),
[BESS frequency shaping](https://doi.org/10.1109/TPWRS.2021.3072833)).

## 5. Multi-agent identifiability and title alignment

The present paper title is *Decoupling-Oriented Coordination of Paralleled
VSGs With Multi-Agent Reinforcement Learning*.  A future method aligns with
that title only if the mathematical object contains all of the following:

1. each physical VSG/BESS has a local dynamic/resource state;
2. each has an independently executed vector action, such as local
   \(u_{P,i},u_{D,i},u_{M,i}\), rather than votes pooled into one scalar;
3. the electrical plant supplies physical coupling and an explicit
   communication graph supplies neighbour messages;
4. deployment uses local observation plus declared messages, with no runtime
   joint-observation action server or central projection;
5. heterogeneous SOC, headroom, location, or modal participation creates a
   real allocation problem;
6. a matched centralized controller is treated as an upper reference and a
   deterministic distributed controller is the primary neural baseline.

Centralized training or a centralized critic is compatible with decentralized
execution, but it is training-only information.  Parameter sharing is also
compatible with multi-agent control, provided actions remain local.  If the
final action is one common scalar or a centrally aggregated projection, the
identified object is a scalar factorization, and the MARL title remains
overstated.

The strongest defensible future claim is not "MARL solves coupling."  It is:

> A neighbour-decentralized residual policy adds measured value over a
> constrained cooperative distributed controller for a validated coupled
> model, while satisfying the same local physical constraints.

## 6. Mandatory non-learning simulation validation

Simulation is necessary.  Mathematical derivation establishes structure and
conditional properties; it cannot establish that the reduction preserves the
nonlinear ANDES plant, saturation events, or the tested operating domain.
Simulation must validate the model before it evaluates a controller.

### Stage A — equilibrium and modal fidelity

- Freeze training/identification and held-out operating-point sets.
- Compare full-DAE and reduced-model mode frequency, damping, participation,
  and branch identity across load, grid-strength, \(M,D\), and SOC conditions.
- Reject a model when the relevant inter-area branch is lost or mode
  hybridization makes the selected reduction non-identifiable.

### Stage B — input authority and coupling

- Apply bounded signed probes separately to \(u_P,u_D,u_M\), with identical
  physical limits and no learning.
- Measure common-frequency, RoCoF, differential/inter-area, voltage, power,
  SOC, energy, saturation, and slew responses.
- Estimate trajectory sensitivities and both common/differential cross gains.
- Freeze the action set only after this comparison.

### Stage C — nonlinear predictive fidelity

- Compare DAE and reduced predictions for complete trajectories, peaks,
  timing, constraint activation, and tail behavior.
- Include disturbances and operating points not used for fitting.
- Construct the MPC uncertainty/tube set from development residuals and test
  coverage on held-out cases without retuning.

### Stage D — deterministic controller validation

- Compare centralized robust MPC, cooperative distributed MPC, and a simple
  local/passivity baseline on the same model/action/information contract.
- On the full ANDES truth model, audit recursive feasibility, constraint
  violations, communication iterations, wall-clock solve time, failures, and
  common/differential physical endpoints.
- Treat a poor but correctly executed controller as a valid negative outcome.

### Kill gates

- If one equilibrium LTI model cannot preserve branch identity and transient
  authority, do not design one fixed LQR from it.
- If an LPV family cannot bound held-out prediction/coupling error, use a
  reduced nonlinear model or narrow the operating domain.
- If the action-authority audit finds no feasible differential improvement,
  do not train MARL on that action space.
- If cooperative DMPC already explains the attainable gain, neural learning
  is optional and cannot be the headline without incremental evidence.
- If local information cannot reconstruct the control-relevant state, the
  study identifies an information limitation, not a MARL algorithm failure.

IEEE 2800 treats voltage/frequency ride-through, dynamic support, protection,
and model validation as distinct obligations rather than one reward score
([IEEE 2800-2022](https://standards.ieee.org/ieee/2800/10453/)).  EMT/HIL and
deployment remain later, separate gates; they are not implied by an ANDES
phasor-domain validation.

## Final R294 answer

- **Has the coupling problem been fully solved?** No.  The previous controller
  isolates some coordinates but does not derive or bound their cross-coupling.
- **Does the proposed direction align with the multi-agent title?** Yes only
  under local physical states, independent vector actions, explicit neighbour
  communication, and decentralized execution.  A scalar aggregation does not.
- **Is LPV-MPC definitively the best model/controller?** Not by itself.  The
  best-supported stack is DAE truth + descriptor-LTI analysis + validated
  descriptor-LTV/LPV robust DMPC, with nonlinear fallback and a passivity or
  dissipativity safety condition.
- **Is simulation validation necessary?** Yes, before controller claims and
  before neural training.  The next eligible execution is the non-learning
  model/authority validation protocol above.
