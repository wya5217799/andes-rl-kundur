# Model and comparison contract

Working title: *Decoupling-Oriented Coordination of Paralleled VSGs With
Multi-Agent Reinforcement Learning*.

Status: pre-draft mathematical contract. This is not manuscript prose and is
not evidence that any proposed controller works.

## Research objective

On the declared phasor-domain multi-VSG plus separate ESD1 plant, determine
whether an independently executed neighbour-local residual MARL policy adds
paired physical value above a validated distributed physics controller while
preserving the same local power, ramp, current, SOC, and energy constraints.
The centralized controller is an upper reference, not an opponent selected to
make MARL win.

The title has two non-negotiable meanings:

1. `decoupling-oriented` means an exact coordinate decomposition with measured
   and retained common/differential cross-coupling, not a hard-decoupled plant;
2. `multi-agent` means local state ownership, declared neighbour messages, and
   independently executed vector actions, with no runtime joint-observation
   action server and no central aggregation to one scalar.

## Exact plant boundary

The validation truth is the sampled-data, index-1 ANDES DAE

\[
E_d(\rho_k)\dot x=f(x,y;\rho_k,p_k^\star,d),\qquad
0=g(x,y;\rho_k,p_k^\star,d),
\]

where \(x\) contains machine, governor, exciter, GENCLS, ESD1 current-lag, and
SOC states; \(y\) contains network voltages/angles and device algebraic
variables; \(\rho=(M,D)\); and \(p^\star\) is the ESD1 active-power request.
For controlled GENCLS unit \(i\),

\[
\dot\delta_i=2\pi f_n(\omega_i-1),\qquad
M_i\dot\omega_i=t_{m,i}-t_{e,i}-D_i(\omega_i-1).
\]

ESD1 power is a separate grid-following network injection. It must not be
written as a direct \(+p_i\) term in the GENCLS swing equation unless that
equivalence is derived after eliminating the network algebraic variables.
The model must include the ESD1 active-current lag, voltage/current capability,
ride-through logic, SOC/efficiency dynamics, and the executable 0.2-s power,
ramp, headroom, and energy projection. GENCLS \(M/D\) updates are sampled
parameter schedules with interpolation, not ordinary unconstrained LTI inputs.

At a regular operating point with nonsingular \(g_y\), the local incremental
model is obtained by the Schur complement:

\[
E_d\,\delta\dot x=A\delta x+B_P\delta p^\star+B_\rho\delta\rho+B_d\delta d,
\]

\[
A=f_x-f_yg_y^{-1}g_x,\quad
B_P=f_p-f_yg_y^{-1}g_p,
\]

\[
B_\rho=f_\rho-f_yg_y^{-1}g_\rho-E_{d,\rho}\dot x^\star.
\]

Hence a parameter appearing only in \(E_d\) has zero direct first-order input
at equilibrium, although it can still change the generalized eigenstructure.
This identity is a required lemma, not an empirical interpretation.

## Common, differential, and graph coordinates

Let \(M_0\) be the frozen positive nominal inertia matrix,

\[
q_c=\frac{M_0^{1/2}\mathbf 1}
{\sqrt{\mathbf 1^\mathsf TM_0\mathbf 1}},
\]

and choose \(Q_d\) so \(Q=[q_c,Q_d]\) is orthogonal. The exact frequency
coordinates are

\[
\xi=Q^\mathsf TM_0^{1/2}\Delta\omega,
\]

with \(\xi_c=\sqrt{\mathbf1^\mathsf TM_0\mathbf1}\,\omega_{\mathrm{COI}}\)
and an invertible \((n-1)\)-dimensional differential coordinate \(\xi_d\).
Angles and relevant controller/storage states receive a compatible invertible
partition. For each frozen schedule,

\[
\begin{bmatrix}\dot x_c\\\dot x_d\end{bmatrix}=
\begin{bmatrix}A_{cc}&A_{cd}\\A_{dc}&A_{dd}\end{bmatrix}
\begin{bmatrix}x_c\\x_d\end{bmatrix}+
\begin{bmatrix}B_{cc}&B_{cd}\\B_{dc}&B_{dd}\end{bmatrix}
\begin{bmatrix}u_c\\u_d\end{bmatrix}+Ew,
\]

where every block is derived from the original Jacobians. The cross blocks are
never set to zero by definition. Coupling is measured with unit-normalized,
finite-horizon incremental \(L_2\) gains (or a stable frozen-schedule
\(H_\infty\) norm) over a prospectively declared operating domain.

Separate the electrical graph \(\mathcal G_e\), whose edge weights come from
the network Jacobian, from the communication graph \(\mathcal G_c\) and the
action graph \(\mathcal G_a\). For the present four-device plant,
\(\mathcal G_a\) is the oriented spanning path
\(E_a=((0,1),(1,2),(2,3))\subset E_c\). Its incidence convention is positive
injection at the first endpoint and equal absorption at the second endpoint,

\[
B_a=\begin{bmatrix}
1&0&0\\
-1&1&0\\
0&-1&1\\
0&0&-1
\end{bmatrix}.
\]

Differential active-power action is represented by the unique tree-edge flow

\[
u_k^d=B_a r_k,\qquad \mathbf1^\mathsf Tu_k^d=0.
\]

This retains \(n-1\) independent differential degrees of freedom rather than
compressing four devices to one two-area scalar or introducing an unobservable
cycle-flow degree of freedom. The fourth communication edge \((0,3)\) carries
messages but no independent actuator coordinate. Edge budgets are allocated so
\(\sum_{e\ni i}\bar r_e\le h_i(x_i)\); then \(|r_e|\le\bar r_e\) preserves
both node headroom and exact command-level fleet neutrality without
elementwise clipping. Exact neutrality is not claimed for achieved inverter
power while unequal current lags, voltages, or ride-through limiters are
active; that mismatch is measured separately.

## Deterministic and neural controller

The deterministic backbone is a neighbour-cooperative robust controller. The
preferred full formulation is tube DMPC,

\[
x_{i,k+1}=A_{ii}x_{i,k}+\sum_{j\in\mathcal N_i^e}A_{ij}x_{j,k}
+B_iu_{i,k}+E_iw_{i,k},\qquad w_i\in\mathcal W_i,
\]

with explicit local state/input/ramp/SOC sets, neighbour messages, tightened
constraints, an invariant error tube, terminal set, finite iteration budget,
and an anytime-feasible fallback. A DAPI controller may be retained as the
lower classical baseline; centralized robust MPC is the upper reference.

The learned policy is only a bounded residual on edge flows:

\[
r_{e,k}=r^{\mathrm{base}}_{e,k}
+\alpha_e(x_k)\tanh\!\left(\pi_{\theta_e}(o_{i,k},o_{j,k},m_{ij,k})\right).
\]

Each node owns its state and local actor; paired edge proposals are exchanged
and antisymmetrized before node incidence aggregation. Centralized critics may
use joint information during training only. A local action-governor or robust
successor-set constraint must keep the residual inside authority reserved by
the deterministic tube. Pointwise action clipping alone is not a stability or
recursive-feasibility argument.

Required proof obligations are: index-1 DAE reduction; exact invertible
coordinate decomposition; direct fleet-neutrality and headroom preservation
of the edge action; conditional robust feasibility and constraint satisfaction
of the deterministic controller; and safety inheritance of the governed
residual. Performance remains empirical.

## Comparator and estimand contract

Every learned arm outputs the same \(n\)-node active-power vector through the
same edge basis and device projection:

| Arm | Runtime information | Role |
|---|---|---|
| local/passivity or DAPI | local plus declared neighbours | lower deterministic baseline |
| cooperative robust DMPC | local plus declared neighbours | strongest distributed baseline |
| centralized robust MPC | joint state | non-deployable upper reference |
| DMPC + neighbour residual MARL | local plus declared neighbours | proposed method |
| DMPC + centralized residual network | joint state | matched single-network reference |

The comparison fixes actuator map, limits, action dimension, scenario bank,
training interactions, tuning budget, seed policy, and endpoint definitions.
It reports absolute value over DMPC separately from the information/deployment
gap to centralized control. No outcome can justify MARL as a universal class.

To distinguish network factorization from runtime information, every neural
arm is placed above the same frozen DMPC and uses the same edge action,
governor, limits, scenario bank, training interactions, total parameter budget,
and seed policy:

| Arm | Network factorization | Runtime information | Primary contrast |
|---|---|---|---|
| SN-J | one residual network | joint | strongest single-network reference |
| SN-N | one block-masked residual network | the same per-edge neighbour features | central hosting at matched information |
| MA-J | independent edge actors | joint broadcast | factorization at matched joint information |
| MA-N | independent edge actors | neighbour only | proposed true distributed execution |

Thus `MA-J - SN-J` estimates factorization under joint information,
`MA-N - SN-N` estimates factorization/distributed execution under matched
neighbour information, and `MA-N - MA-J` estimates the locality penalty. This
factorial analysis replaces any unidentifiable binary claim that centralized
and multi-agent architecture alone caused an observed difference.

## Topology decision and claim ceiling

The present plant is a modified Kundur two-area phasor-domain system with four
radially attached VSG-proxy plus separate ESD1 pairs. Its electrical graph,
the manually declared four-agent communication ring, the edge-action basis,
and the disturbance set are different mathematical objects and must be drawn
and reported separately.

The topology is **allowed** for equation-to-implementation reconciliation and
controller development, and **qualified** for a fixed-network study of
common/differential coupling and independently executed distributed control.
It is **blocked** as evidence of an "advanced topology", topology
generalisation, unified GFM-BESS control, EMT behaviour, or deployment. The
value of Kundur is its interpretable inter-area mechanism, not network novelty.

No electrical-line redesign is required for the first paper. The smallest
prospective modification is resource heterogeneity at the existing four ESD1
locations: frozen differences in initial SOC, power/current rating, ramp rate,
available energy, or headroom, combined with location-specific disturbances.
This creates a real distributed allocation problem without confounding
controller architecture with network redesign. The communication graph must
then be justified from a declared communication budget or electrical
sensitivity, rather than called the electrical neighbour graph. Physical
topology variation, if later claimed, requires multiple valid training graphs
and unseen held-out graphs; line-impedance variation alone establishes only
parameter or grid-strength robustness.

## Modeling and simulation workflow

Modeling and simulation proceed iteratively, but formal evaluation is never
used to redesign the model. The prospective sequence is:

1. **Implementation map:** freeze DAE variables, bases, signs, ESD1 equations,
   sampled update order, projections, graphs, and operating domain. Run only a
   nominal readback canary plus unit/sign/SOC/slew tests.
2. **Coordinates and authority:** derive the invertible inertia-weighted
   transform, inverse, every cross block, and edge-incidence action. Run small
   signed active-power probes at representative operating points. The previous
   0.444 cross/self observation already rejects hard decoupling against the
   0.20 development ceiling; subsequent models retain the cross blocks.
3. **Reduced predictor:** derive a trajectory-linearized discrete LTV/LPV
   predictor and mismatch set from development traces; validate on untouched
   held-out traces. The previous coarse static LPV is not reused as the final
   predictor.
4. **Deterministic control:** validate DAPI, coupling-aware tube DMPC, and
   centralized robust MPC before any learning. Require zero physical/solver
   violations, recursive-feasibility/fallback evidence, and real-time margin.
5. **Residual-headroom gate:** on development-only cases, test whether a safe
   outcome-seeing residual can improve both registered endpoints by at least
   2% over frozen DMPC, with both paired 95% upper bounds below zero and no
   guard failure. Also require adequate local/neighbour observability and
   nonzero residual authority.
6. **Training and EVAL:** train only if every preceding gate passes. Freeze the
   architecture, information sets, budgets, seeds, endpoints, and EVAL profile,
   then use a new untouched bank for paper-facing evaluation.

Candidate reduction gates, to be frozen before data generation, are: DAE
residual at most \(10^{-8}\), relevant-mode frequency error at most 5%, absolute
damping error at most 0.01, participation-vector cosine at least 0.90,
held-out coordinate-response NRMSE at most 0.15, peak error at most 10%, event
timing within one 0.2-s sample, and complete inclusion in the declared mismatch
set (or a prospectively registered probabilistic coverage bound).

Full ANDES jobs remain capped by repository governance at three concurrent WSL
Python processes. The three shards may run independently after seal; algebra,
Jacobian processing, reduction fitting, proof work, and report generation may
use the remaining host cores concurrently. Increasing the ANDES cap requires a
separate governance decision and resource/reproducibility canary, not ad-hoc
oversubscription during a paper-facing round.

The current primary-source literature audit is recorded in
`working/hybrid_control_literature_note.md`. Its bounded conclusion is that
end-to-end RL remains an active empirical method but is not the assurance
default for this safety-critical controller. The proposed contribution is
therefore the independently executed, governed residual above a structured
distributed controller, conditional on a measured residual gap.

## Equation-to-implementation reconciliation

This section is the source-audited implementation contract as of 2026-08-03.
It reconciles repository source with the installed ANDES 2.0.0 device models;
it is not simulation evidence. Existing R294 utilities are candidate code only
and their historical outputs do not become evidence for this manuscript line.

### Model of record and physical base

The prospective plant is a new explicit configuration of
`AndesMultiVSGEnvV4Storage`, not the class defaults used to reproduce legacy
headline numbers. It freezes the following choices:

| Object | Prospective model-first value | Executable source or reason |
|---|---|---|
| System base | 100 MVA | ESD1 external commands and all reported power use system-base p.u. |
| Physical nominal frequency | 60 Hz | Installed Kundur `GENROU`, lines, added `GENCLS`, and ESD1 all use 60 Hz |
| Legacy control nominal | excluded | `scenarios.contract.KUNDUR.fn=50` may remain for legacy reproduction but cannot enter this line's equations, controllers, or endpoints |
| Controller period | 0.2 s | `KUNDUR.dt` and `AndesBaseEnv.DT` |
| GENCLS update | frozen during active-power probes; later schedules require explicit device-to-system-base conversion before five 0.04-s substeps | the legacy `AndesBaseEnv.step` mixes input- and system-base `M/D` values and is not admissible unchanged |
| Original Kundur G4 | retained, `zero_g4_inertia=False` | the class default silently changes G4 to `M=0.1,D=0`; this line does not inherit that legacy alteration |
| Default line outage | disabled | the source case opens `Line_8` between buses 8 and 9 at 2 s unless its `Toggler` is disabled |
| Stochastic disturbance and communication failure | disabled during model validation | signed probes require paired deterministic initial conditions |

The four controlled locations are indexed in executable order

| Agent | VSG proxy | ESD1 | controlled bus | radial parent bus | area |
|---:|---|---|---:|---:|---:|
| 0 | `VSG_1` | `R272_BESS_1` | 12 | 7 | 1 |
| 1 | `VSG_2` | `R272_BESS_2` | 16 | 8 | 1 |
| 2 | `VSG_3` | `R272_BESS_3` | 14 | 10 | 2 |
| 3 | `VSG_4` | `R272_BESS_4` | 15 | 9 | 2 |

Each `VSG_i` is a 200-MVA `PV+GENCLS` proxy. The model-first nominal design
values are device/input-base `M=200` and `D=100`; because both ANDES parameters
carry `power=True`, their coherent live system-base values on a 100-MVA system
are `M=400` and `D=200`. Each ESD1 is a separate 36-MVA grid-following device
at the same bus. The plant also contains the four original Kundur `GENROU`
machines, their pre-setup IEEEG1/EXST1 controllers, and a separate 100-MVA
low-inertia `GENCLS` wind proxy at bus 8. These are all part of the full DAE and
cannot be removed from the Schur complement by narrative convention.

### Executable GENCLS and ESD1 equations

For every controlled `GENCLS`, installed ANDES 2.0.0 implements

\[
\dot\delta_i=2\pi f_{n,i}(\omega_i-1),\qquad
M_i\dot\omega_i=t_{m,i}-t_{e,i}-D_i(\omega_i-1),
\]

with `omega` in p.u. of 60 Hz, `delta` in rad, and `M=2H`. The network active
power readback is

\[
P_{e,i}=v_{d,i}I_{d,i}+v_{q,i}I_{q,i}.
\]

The swing equation uses electromagnetic torque `te`, not the convenience
readback `Pe`; equality must not be assumed away from the operating point.
ANDES stores `M` and `D` in its live system-base arrays after applying the
device-to-system coefficient `Sn/Ssys`. A model-first schedule must declare its
input base, convert once, interpolate live system-base coefficients over the
five TDS segments, and log both representations. Actual arrays `GENCLS.M.v`
and `GENCLS.D.v`, rather than target telemetry `M_es` and `D_es`, are the
required execution readbacks.

For the current ESD1 configuration, the static generator has zero scheduled
active power, `ddn=0`, and the external interface writes an absolute
system-base command to `Pext0` through `DG.set_paux()`. Thus, while enabled,

\[
P_{\mathrm{sum}}=P_{\mathrm{ext}}+P_{\mathrm{ref}}+P_{\mathrm{drp}}
=P_{\mathrm{ext}}.
\]

The ESD1/PVD1 path limits `Psum` to `[-pmx,pmx]`, divides by sensed voltage
\(v_p=\max(v,0.01)\), applies active-current priority, ride-through recovery
coefficients, the SOC-dependent current box, and the active-current lag

\[
T_{ip}\dot I_{p,\mathrm{out}}=I_{p,\mathrm{cmd}}-I_{p,\mathrm{out}},
\qquad P_{\mathrm{grid}}=v I_{p,\mathrm{out}}.
\]

Here `tip=0.02 s`, `pmx=1.0` on the 36-MVA device base, and `ialim=1.0`.
Positive \(P_{\mathrm{grid}}\) is network injection and battery discharge. The
SOC equation is

\[
T_f\dot{SOC}=\frac{S_{sys}}{3600E_n}
\begin{cases}
-P_{\mathrm{grid}}/\eta_D,&P_{\mathrm{grid}}\ge0,\\
-P_{\mathrm{grid}}\eta_C,&P_{\mathrm{grid}}<0,
\end{cases}
\]

with `Tf=1`, `En=28 MWh`, `SOCinit=0.5`, bounds `[0.2,0.8]`, and
`eta_C=eta_D=0.9848857802`. Because the environment does not override ESD1's
recovery settings, the installed 60-Hz defaults remain active: frequency
breakpoints `[59.5,59.7,60.3,60.5]` Hz and voltage breakpoints
`[0.88,0.90,1.10,1.20]` p.u. They are part of the validation truth, not an
optional prose detail.

Before the ESD1 equations, the repository applies an external discrete
projection to the absolute request. For each device and 0.2-s interval its
nominal limits are

\[
|p_i|\le0.36\ \text{system p.u.},\qquad
|p_{i,k}-p_{i,k-1}|\le0.072\ \text{system p.u.},
\]

plus the voltage-current limit, SOC boundary, and one-step energy limit. The
implemented order is ramp, nameplate power, voltage-current capability, SOC,
then energy. The projected setpoint is still not achieved power.

The three power layers have distinct meanings and all must be logged:

| Layer | Required readback | Meaning |
|---|---|---|
| request | `bess_requested_power_system_pu` | controller output before feasibility handling |
| external command | `bess_commanded_power_system_pu` and saturation reasons | value written to ESD1 `Pext0` after the repository projection |
| plant execution | ESD1 `Pext0`, `Psum`, `Ipcmd_y`, `Ipout_y`, `Ipmin`, `Ipmax`, recovery coefficients, `v`, `SOC`, and `v*Ipout_y` | internally limited command, dynamic current, achieved power, and energy state |

The current environment records only part of the third layer. Therefore
`bess_constraint_violations=[]` is not yet a complete physical-constraint
guard.

### Sampled update order

At control boundary \(t_k\), the prospective harness must preserve and log this
order:

1. read the physical 60-Hz frequency, ESD1 SOC/voltage, previous external
   command, and all controller-owned local states;
2. compute local DAPI/DMPC requests and neighbour messages using only values
   available at \(t_k\);
3. allocate any differential tree-edge residual inside endpoint headroom and
   run the external power projection;
4. write the absolute projected command to ESD1 `Pext0`;
5. hold that power setpoint while interpolating any separately scheduled
   `GENCLS M/D` target over five 0.04-s TDS segments;
6. at \(t_{k+1}\), read achieved power, SOC, limiter states, actual `M/D`, and
   DAE status before updating controller memory.

A reset first integrates the unperturbed model to 0.5 s and then edits the PQ
load. Consequently, the first command after reset uses the pre-disturbance
sample; the disturbance and held command take effect in the following TDS
interval. This one-sample causal timing must be retained in every comparator.

### Four distinct graphs

- The bus-level electrical graph is the installed Kundur network plus radial
  links `7-12`, `8-16`, `10-14`, and `9-15`. An agent-level electrical
  sensitivity graph is derived from the reduced network Jacobian and may be
  dense; it is not inferred from bus adjacency.
- The communication graph is the fixed undirected ring with edges
  `{(0,1),(1,2),(2,3),(0,3)}`.
- The active-power action graph is the oriented tree
  `((0,1),(1,2),(2,3))` with the positive-source convention in \(B_a\) above.
  The legacy inertia module uses the opposite incidence sign and must not be
  imported as this line's active-power action matrix.
- The disturbance graph identifies the edited PQ device or physical outage.
  Model-validation probes use explicit locations and keep the case's implicit
  `Line_8 @ 2 s` outage disabled.

### Reconciliation findings and repair gate

| ID | Severity | Finding | Required repair before evidence generation |
|---|---|---|---|
| MF-01 | BLOCKER | Legacy observations/rewards can label the 60-Hz ANDES plant as 50 Hz. | Make the detected 60-Hz base the only frequency base in the model-first harness, controllers, endpoints, and traces. |
| MF-02 | BLOCKER | Existing telemetry does not expose the full ESD1 internal limiter/current path. | Add the third-layer readbacks above and guard internal as well as external constraints. |
| MF-03 | BLOCKER | Existing Stage-A code consumes ANDES's reduced `EIG.As`; it does not reconstruct or verify \(E_d,f_x,f_y,g_x,g_y,B_P,B_\rho\). | Implement an explicit descriptor/Jacobian extractor and numerical Schur-complement identity checks. |
| MF-04 | BLOCKER | `helmert_coordinates()` is unweighted and does not implement the frozen inertia-weighted transform or its inverse. | Implement \(Q,M_0^{1/2}\), the inverse map, and block reconstruction tests. |
| MF-05 | MAJOR | Legacy inertia incidence and active-power edge allocation use opposite signs. | Define one new active-power incidence constant from the matrix above and test each signed edge end to end. |
| MF-06 | BLOCKER | `GENCLS.M/D` are power-base converted at setup, but the legacy step writes nominal-looking values directly in system base; current initialization has `M=400` then the first zero-action step writes `M=200`, while `D` is separately overwritten to 100. | Introduce an explicit device/system-base contract, initialize through `base='device'`, cache actual live values, and bypass all `M/D` writes during active-power-only probes. |
| MF-07 | MAJOR | The V4 default silently reduces original Kundur G4 to `M=0.1,D=0`. | Use an explicit model-first config with `zero_g4_inertia=False`; never rely on the class default. |
| MF-08 | MAJOR | The BESS contract is scalar/identical across devices. | Add immutable per-device SOC, power/current, ramp, energy, and availability parameters before the heterogeneity study. |
| MF-09 | MAJOR | DAPI utilities exist, but no tube-DMPC, centralized robust MPC, terminal set, invariant tube, or anytime fallback is implemented. | Treat all such controllers as designs until separate tests and a prospective deterministic-control round pass. |
| MF-10 | MAJOR | Zero-sum edge allocation guarantees requested/commanded residual neutrality, not exact achieved inverter-power neutrality. | Report achieved fleet imbalance and include it in the predictor mismatch set; weaken any physical-neutrality wording accordingly. |
| MF-11 | MINOR | The first response sample follows a pre-disturbance controller observation. | State and test the one-sample timing rather than plotting it as zero-delay feedback. |

Current domain verdict: **BLOCK** the present implementation as claim-bearing
evidence; **ALLOW** a prospective repair plus non-learning canary; **BLOCK**
controller-performance or neural training conclusions. Presentation review is
not applicable because no manuscript prose or result figures exist.

The claim ceiling after reconciliation, but before any new result, is limited
to: “an implementation-faithful contract and prospective validation protocol
were specified for one modified Kundur phasor-domain plant.” It does not support
controller efficacy, stability, safety, MARL value, or generalisation.

## Stage-0 and Stage-1 non-learning probe contract

These line-level values are frozen before data access. A future atomic research
question and create-only seal must copy them, hash the implementation sources,
and name any justified amendment. No run is authorized by this document.

### Stage 0: nominal readback canary

- Plant: the explicit model-first configuration above, including
  `zero_g4_inertia=False`, `DISABLE_TOGGLER=1`, deterministic disturbance mode,
  and zero communication failures.
- Initialization: converged power flow followed by the existing 0.5-s
  disturbance-free TDS initialization.
- Horizon: five 0.2-s control intervals after initialization.
- Inputs: zero `M/D` increments, zero ESD1 power requests, and no PQ edit.
- Required gates on every sample: power flow and TDS success, `exit_code=0`,
  finite state/algebraic arrays, detected nominal frequency exactly 60 Hz,
  time increment `0.2 +/- 1e-9 s`, equilibrium DAE residual
  `max(max(abs(f)),max(abs(g))) <= 1e-8`, actual controlled system-base
  `M=400` and `D=200` within `1e-10`, request/command/actual ESD1 power within
  `1e-8` system p.u.
  of zero, SOC within `[0.2,0.8]` with drift at most `1e-8`, all internal
  limiter variables finite, and `Line_8` in service throughout.
- Structural gates: the node/device table, communication ring, action-tree
  rank three, incidence column signs, and all source-to-readback indices match
  the sealed contract.

Any failure stops Stage 1. It is not repaired by relaxing a threshold after
inspection.

### Stage 1: signed active-power path and local-linearity probes

Use three development operating points, all with the original Kundur G4
retained and no load disturbance:

| Point | device-base VSG `M` | device-base VSG `D` | live system-base `M/D` | `Line_4/5/6` r/x scale | all-device SOC |
|---|---:|---:|---:|---:|---:|
| OP0 | 200 | 100 | 400 / 200 | 1.0 | 0.50 |
| OP1 | 150 | 75 | 300 / 150 | 1.0 | 0.30 |
| OP2 | 250 | 125 | 500 / 250 | 2.0 | 0.70 |

At each point run one zero-input baseline and paired signs for four independent
input coordinates:

\[
p^{c,+}=+0.05\mathbf1,\quad p^{c,-}=-0.05\mathbf1,
\]

and, for every action-tree column \(b_e\),

\[
p^{e,+}=+0.05b_e,\quad p^{e,-}=-0.05b_e.
\]

Power is in system-base p.u. Each pulse lasts five samples (1.0 s), followed by
20 zero-request samples (4.0 s). The paired runs share the same initialization,
solver settings, and source hashes. No `M/D` action or legacy `M/D` decoder is
executed during a power probe.

The prospective Stage-1 gates are:

1. every trace passes the Stage-0 execution, timing, and finite-value guards;
   algebraic residual and solver convergence pass at every sample, while the
   differential right-hand side is allowed to be nonzero during the transient;
2. requested and external-command vectors equal the frozen pulse within
   `1e-12` after projection, with no external or ESD1 internal limiter active;
3. actual `GENCLS M/D` remain at the scheduled operating-point values within
   `1e-10`;
4. common and edge central-difference responses have L2 signal-to-baseline
   numerical drift at least 20, correct achieved-power sign, and a final active
   sample within 5% of the external command;
5. every edge request and external command sums to zero within `1e-12`; achieved
   residual fleet imbalance is reported and is at most 5% of the commanded
   residual L1 norm at the final active sample;
6. positive achieved power decreases SOC, negative achieved power increases
   SOC, all SOC values remain in `[0.2,0.8]`, and no current, power, ramp, SOC,
   energy, voltage-recovery, or frequency-recovery guard fails;
7. the paired midpoint nonlinearity ratio is at most 0.25 at the median point
   and 0.50 at the worst point;
8. both common-to-differential and differential-to-common finite-horizon gains
   are finite and reported. They have no pass-by-smallness gate: measured cross
   coupling is retained in the next predictor.

Passing Stage 1 establishes only that the commanded ESD1 path is causal,
signed, feasible in the declared small-signal domain, and sufficiently
observable for predictor construction. Failure is an authority/modeling NO-GO,
not motivation for neural training.

### Predictor gates carried forward

Only after Stages 0 and 1 pass may a trajectory-linearized discrete LTV/LPV
predictor be fitted on new development traces and assessed on untouched
holdouts. The frozen pointwise limits remain: mode-frequency relative error at
most 5%, damping-ratio absolute error at most 0.01, participation-vector cosine
at least 0.90, coordinate-response NRMSE at most 0.15, peak error at most 10%,
event timing within one 0.2-s sample, and complete membership in the declared
mismatch set unless a prospective probabilistic coverage target replaces that
deterministic requirement. The descriptor reduction, transform/inverse, and
full block reconstruction must also pass algebraic unit tests before controller
development.

## Training and EVAL gates

1. **DAE gate:** exact equilibrium, unit/sign/readback, update-order, and
   algebraic-regularity checks pass on every declared operating point.
2. **Reduction gate:** the control-relevant branch is tracked on all held-out
   points; frequency error, damping error, mode-shape agreement, trajectory
   error, peak timing, and mismatch-set coverage meet frozen numeric limits.
3. **Coupling/authority gate:** signed probes establish feasible active-power
   authority and quantify both cross directions. Hard decoupling is rejected
   unless a preregistered cross-gain ceiling is met.
4. **Deterministic gate:** distributed control has zero solver/physical
   violations, meets runtime and feasibility limits, and leaves a nonzero
   paired residual gap relative to a frozen outcome-seeing or centralized
   upper reference.
5. **Neural GO/NO-GO:** only after Gates 1--4 may training start. On a new
   sealed bank, residual MARL must improve both registered primary endpoints
   over DMPC by at least 2%, with both 95% interval upper bounds below zero,
   every predefined seed directionally agreeing, and no guard failure.
6. **EVAL:** EVAL-v2 audits frozen trace integrity, physical endpoints,
   uncertainty, tails, action use, and constraint execution. It remains
   `EXTERNAL_AUTHORITY_REQUIRED`; feed/claim/verdict state owns evidence.

The equation-to-implementation reconciliation and non-learning probe design
are now frozen at manuscript-line level. The next task requires a new atomic
research question authorizing only the MF-01--MF-07 implementation repairs and
the Stage-0 canary. Stage 1 remains conditional on Stage 0, and no neural
training is authorized by this contract.
