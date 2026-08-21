# Methods draft — Sections III-IV (paper-writer, 2026-08-14)

Status: first draft of Sections III (Plant and implementation contract) and
IV (Gate methodology). Every factual statement is bound to the line's
registered sources; delivery notes at the end list what still needs the
verified literature pool. Prose only; no result tables are duplicated here.

---

## III. Plant and implementation contract

This section fixes the executable plant and the implementation contract
that every later stage validates against; no later result is measured on a
plant different from the one specified here.

### A. Test system

The study object is a modified Kundur two-area phasor-domain system
implemented in the ANDES 2.0.0 simulation framework on a 100 MVA, 60 Hz
base. It retains the four original GENROU synchronous machines with their
IEEEG1 governors and EXST1 exciters, together with a low-inertia wind proxy
at bus 8. Four controllable nodes are added, each composed of a network bus,
a 200 MVA VSG proxy (PV + GENCLS), and a separate co-located energy storage
unit (PV + ESD1). The storage units are the only actuators in this line:
VSG-proxy inertia and damping are frozen plant parameters, not online
actions. Table III.1 lists the four nodes; the VSG proxies have device-base
M = 200, D = 100, i.e. system-base M = 400, D = 200 on the 100 MVA base,
and the storage units are rated 36 MVA with 28 MWh energy capacity, initial
state of charge (SOC) of 0.5, and SOC bounds [0.2, 0.8].

Table I. Four controllable storage nodes: parent network bus, device bus,
and area for each VSG proxy and its co-located energy storage unit. Source:
model contract (paper/decoupling_marl_model_first/working/model_contract.md).

| Node | Parent bus | Device bus | Area |
|---|---|---|---|
| 1 | 7 | 12 | 1 |
| 2 | 8 | 16 | 1 |
| 3 | 10 | 14 | 2 |
| 4 | 9 | 15 | 2 |

### B. Executable device laws

The validation truth is the sampled-data index-1 differential-algebraic
equation (DAE) model
E_d(\rho_k) x' = f(x, y; \rho_k, p*, d_k), 0 = g(x, y; \rho_k, p*, d_k),
where x collects machine, governor, exciter, GENCLS, storage current-lag,
and SOC states, y the network and device algebraic variables, \rho the
frozen plant parameters, p* the four-dimensional storage active-power
request, and d the physical disturbance. Each VSG proxy follows the GENCLS
swing equations; the storage unit realizes its command through an
active-current lag T_ip I_p' = I_p,cmd - I_p with T_ip = 0.02 s, a
voltage-dependent current path, ride-through recovery, and an SOC law with
charge/discharge efficiencies 0.9848857802, all subject to the installed
60 Hz default recovery breakpoints, which are part of the validation truth
rather than optional detail.

### C. Three power layers

The implementation distinguishes three power layers that are all logged:
the controller request p*, the external command p_cmd after the repository's
deterministic projection, and the achieved power read back from the plant.
The projection enforces, in order, ramp (0.072 p.u./step), nameplate power
(0.36 p.u.), voltage-current capability, SOC bounds, and one-step energy
limits. Reporting only the request would be insufficient: the controller
commands power, it does not set achieved power, and the internal storage
limiters can act without appearing in the request record.

### D. Graphs and action basis

Four distinct graphs are kept separate in implementation and in reporting.
The electrical graph is the Kundur network plus the four radial links. The
communication graph is the fixed undirected ring {(1,2),(2,3),(3,4),(1,4)}.
The active-power action graph is the oriented tree ((1,2),(2,3),(3,4)) with
incidence B_a; a tree-edge flow u^d = B_a r satisfies 1' u^d = 0, so a
differential-only action redistributes power among the four nodes and
cannot create net fleet power. The fourth communication edge carries
messages but no independent actuator coordinate. The disturbance graph
records the edited PQ device or physical outage. An edge-action governor
bounds each differential coordinate to |r_e| <= 0.05 p.u. with a per-step
change limit of 0.05 p.u., inside the endpoint headroom and node-level
projection.

### E. Implementation reconciliation

Before any result was accepted, the intended equations were reconciled
against the executable simulator source, producing a repair list whose items
are material to measured endpoints: the legacy observation path labelled the
60 Hz plant as 50 Hz; the GENCLS M/D write path mixed device and system
bases; a default silently reduced the original G4 inertia; the storage
telemetry did not expose the internal current-limiter path; and the legacy
incidence sign of the inertia module is opposite to the active-power action
basis. The reconciled contract, the repaired guards, and the one-sample
causal timing between disturbance, command, and achieved power are frozen
for all subsequent stages. These repairs are reported as part of the
methodology contribution, not as peripheral software notes.

## IV. Gate methodology

This section defines the gate sequence as a decision procedure: every
stage is pre-registered, sealed, fail-closed, and its verdict is
attributable to one changed factor.

### A. Gate sequence and sealing discipline

Every stage is a pre-registered, fail-closed gate over the unchanged plant.
Each gate freezes a written contract (what changes, what is fixed, the
decision tree, and the stopping outcomes) before data access; runs a
rehearsal over the identical verification path; seals source and case
hashes; and writes results into a create-only root that cannot be edited
after inspection. A failed gate stops the route; thresholds are never
relaxed after inspection, and a retry is a new prospectively registered
attempt. For the physical closed-loop stage, the process budget was
measured and frozen before the seal, and every worker pinned its native
numerical threads to one.

### B. Stage 0 and Stage 1 canaries

Stage 0 is a nominal readback canary: a disturbance-free five-sample
trajectory with zero requests that must show power-flow and time-domain
simulation (TDS) success,
equilibrium DAE residual at most 1e-8 (measured 2.9e-9), exact live
system-base M = 400 and D = 200 readbacks with zero M/D write count, zero
request/command/achieved power, zero SOC drift, all internal limiter
variables finite, and Line_8 in service throughout. Stage 1 applies signed
active-power probes: common pulses +/-0.05 * 1 and independent edge pulses
+/-0.05 * b_e for every action-tree column, each held five samples and
released for twenty. Passing requires signal-to-baseline separation of at
least 20 in L2, correct achieved-power sign, a final active sample within
5% of the command, exact request-level fleet neutrality, achieved residual
fleet imbalance at most 5% of the commanded residual L1 norm, monotone SOC
direction, and midpoint nonlinearity ratios at most 0.25 at the OP0 point
and 0.50 across all points; the measured ratios were 0.003 and 0.004. The same stage also
measured the retained common/differential cross gains: across twelve
coordinate/operating-point pairs, cross-to-self L2 ratios ranged from 1.11%
to 3.90%, so hard decoupling was rejected prospectively and the cross
blocks were retained in every later model.

### C. Coordinates and model qualification

Control coordinates are the inertia-weighted common/differential transform
xi = Q' M0^{1/2} \Delta\omega with one common coordinate and three
differential coordinates; the incremental plant model is obtained by Schur
complement elimination of the network algebraic variables, and control and
physical-disturbance inputs are kept as separate channels z_{k+1} = A z_k +
B_u u_k + B_d d_k rather than a shared input. Reduced order-12 candidates
were constructed at two locally defined operating points and qualified on a
fresh finite bank: the registered ceilings were normalized root-mean-square
error (NRMSE) at most 0.15 and peak
residual at most 0.20, with worst measured order-12 NRMSE 0.130 and peak
residual 0.087; the full sampled model measured worst NRMSE 0.021. This
qualification is point-specific: it neither validates interpolation nor
claims a general linear parameter-varying (LPV) law.

### D. Deterministic baseline

The retained deterministic reference is a centralized constrained
receding-horizon controller acting in the four coordinates. It uses the
order-12 separate-input model, a disturbance-augmented estimator, and a
direct quadratic program (QP) solve at every 0.2 s control instant with
node power (0.36 p.u.),
ramp (0.072 p.u.), SOC, and energy constraints, falling back to a bounded
ramp toward zero if the QP is unavailable. Its request passes through the
same physical projection as every other arm. A second, endpoint-local
deterministic law (linear feedback on the frequency and rate difference of
each edge's two endpoints) exists and passed its own bounded holdout gate,
but it is not the headline reference of this paper: the centralized
controller is the upper reference, and the comparison discipline below
fixes every arm's actuator map, limits, and projection.

### E. Residual-headroom and diagnostic gates

The registered endpoints are the common-coordinate integral absolute error
and the summed differential-coordinate squared error over a 25-sample
transient. A residual action is defined as a zero-common edge allocation
p^r = B_a r passed through the exact physical projection, and the
residual-headroom gate asks whether any residual improves the common
endpoint by at least 2% without differential degradation and without any
guard failure. Three diagnostic layers make a negative answer attributable:
(i) an outcome-seeing offline upper bound (smooth convex oracle) that
ignores information constraints; (ii) causal per-edge map families (affine,
RBF kernel ridge, 5-nearest-neighbour, and quadratic) fitted offline with
leave-one-scenario-out validation over standardized 15-field endpoint-local
observations, extended with one-hop state messages and with four-step
model-prediction messages in two further variants; and (iii) an action-basis
ablation that adds one fleet-equal common channel to the three-edge basis
and re-solves the same physically constrained QP. These programs test
whether a residual action exists; they do not define how a causal runtime
controller would obtain one, and no neural network, reinforcement learning
policy, or training object is involved in any of them.

### F. Paired evaluation discipline

Every claim-bearing comparison is paired: the two arms share
initialization, disturbance, timing, simulator settings, actuator path, and
guards, and differ only in the registered variable (controller versus zero
control; one action basis versus another; one information family versus
another). The formal physical bank contains sixteen scenarios (two
operating points, four active-load locations, two signs), each executed as
a matched pair of 25-sample trajectories. Two zero-action and sixteen
signed-authority canaries had to pass before the bank was released. A 5%
no-harm limit applies to every scenario. Holdout cases exist but remain
unexamined for the headroom gates; no holdout conclusion is claimed.

---

## Delivery notes (not part of the manuscript)

1. Citations still to be added from the verified literature pool: the
   ANDES framework paper, the Kundur two-area system reference, and the
   OSQP/cvxopt solver references are now registered in the differentiation
   memo ([40]-[43]); the Yang et al. TPWRS study is registered as a single
   2023 entry (DOI 10.1109/TPWRS.2022.3221439).
2. Table III.1 will carry a figure/table caption with the source pointer to
   the model contract when typeset.
3. All numbers in this draft come from the bound feeds and claims
   (R306/R312/R341/R344, CLM-0740/CLM-0770/CLM-0900/CLM-0910); none is
   invented. The Results sections (V-VI) are drafted separately.
