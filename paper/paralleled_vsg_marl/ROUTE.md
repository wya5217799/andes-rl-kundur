# Fixed-title execution route

## Decision

Freeze the prior ICEMS, SCI-upgrade, and model-first lines as evidence lines.
This directory is the only active route for **Decoupling-Oriented
Coordination of Paralleled VSGs With Multi-Agent Reinforcement Learning**.
Old work supplies implementation, failure boundaries, and evaluation
discipline; it cannot combine into title evidence.

The object keeps the Yang et al. abstraction
(DOI `10.1109/TPWRS.2022.3221439`): multiple VSG units interact through one
network, each using local and permitted neighbour signals. R369 stops direct
inertia/damping action learning. The successor keeps the per-VSG object and
multi-agent information pattern but changes the actuator to an
energy-constrained active-power reference owned by each VSG unit. The paper
is an object and algorithm reference, not a numerical Simulink target.

## Title contract

| Title term | Minimum evidence on one common object | Immediate rejection |
|---|---|---|
| Paralleled VSGs | Multiple explicitly identified ANDES VSG units interact through the same network, each independently actuated. | Edge actors, an area scalar, or one central action renamed as multiple VSG agents. |
| Decoupling-Oriented | Preregistered physical differential-mode/oscillation endpoints improve against a matched strong deterministic baseline. | Only reward, average frequency, or coordinate relabelling improves. |
| Coordination | Message-enabled per-VSG execution beats independent/no-message and matched non-learning residual ablations. | Centralized critic or shared parameters treated as runtime coordination. |
| MARL | Multiple actors trained jointly or in an explicit multi-agent game, evaluated with independent runtime actions. | A single policy, scalar factorization, or offline optimizer called MARL. |

`decoupling` is narrow: suppression of inter-VSG dynamic coupling and
differential oscillation from heterogeneous inertia, droop, and disturbance
distribution. Electromagnetic P/Q decoupling, reactive sharing, circulating
current, switching dynamics, and protection are outside the first paper
(plant fidelity).

`Decoupling-Oriented` is an input-output claim, not a coordinate name. With
`z_c = (1/4) 1^T Delta f` and `z_d = T_d Delta f` (inter-area plus two
intra-area differential coordinates), a transform alone is not decoupling:
the closed-loop signed-response operator must report its off-diagonal
common/differential blocks. Minimum joint evidence: lower off-diagonal
cross-coordinate response energy on a fresh paired probe bank; lower
disturbance-driven differential-frequency energy and settling; no material
degradation in common frequency, worst-unit peak, RoCoF, failures,
saturation, energy, or control stress; and for the MARL claim, an ablation
removing neighbour messages or the cross-coordinate objective removes the
increment. Coordinates are physical arithmetic projections, not asserted
eigenmodes. Hard diagonalization, stability certification, and P/Q
decoupling stay outside the claim.

## Current gate

Object/action and permission-matched design gates are complete (`CLM-0975`,
`CLM-0980`); the first bank invalidity is `CLM-0985`; the outcome-blind
correction and pretraining decision are `CLM-0990`. R370-R373 validate the
VSG-owned energy-constrained power-reference object, achieved-power
accounting, and common/differential authority (`CLM-1000`, `CLM-1005`,
`CLM-1010`) — object/actuator prerequisites, not controller results.

R374 is identity-invalid (`CLM-1015`). R375 corrects the identity and
returns the terminal stop `CLM-1020`: the frozen deterministic
power-reference formulation fails its held-out physical guard. No retry,
gain change, headroom test, or training. Title terms remain prospective.

The successor hypothesis selects **feasibility-native four-VSG node
actions**; the prospective contract is
`working/feasibility_native_four_vsg_contract.md`. Route:

1. preserve the four object-matched VSG agents, energy accounting, physical
   endpoints, and matched-baseline discipline of R365-R373;
2. each VSG actor emits one scalar normalized action mapped directly into
   that VSG's current power/ramp/energy-feasible interval;
3. execute the four node commands independently, no scalar/edge aggregation;
   analyse one common and three differential coordinates as endpoint views;
4. the unchanged outer VSG-port projector is identity-only; any outer repair
   invalidates the seam;
5. the same node-action map serves deterministic, random, independent-RL,
   no-message MARL, message-enabled MARL, and objective-ablation arms;
6. require a separately registered deterministic physical gate followed by a
   non-learning conditional-headroom gate before training.

The route uses no supervised neural residual, so it does not depend on a
nonzero residual label. Direct MARL, if authorized later, learns the four
normalized feasible actions themselves. This removes the R375
post-controller projection and Model-First residual-target mechanisms, but
does not guarantee deterministic efficacy or a learning increment.

Gate A is implementation-qualified in `scratch` (four literal node actors,
command locality, feasible-interval coverage, common-plus-three-differential
rank, malformed-action rejection, randomized states, outer-projection
identity). Not experimental evidence.

Gate B (`working/gate_b_deterministic_physical_contract.md`, `CLM-1025`):
zero/local/neighbour arms keep identity with full action rank on the
60-record development bank, but no frozen distributed gain pair clears
eligibility — R376 stops `STOP-DEVELOPMENT-NO-CANDIDATE`. The seam stays
qualified; the law family does not.

Gate B-2 (`working/gate_b2_deterministic_physical_contract.md`): high-pass
mutual damping, differential oscillation primary, probe cross no-harm
ceiling. R377 stops on an unsatisfiable settling-floor rule (`CLM-1030`);
R378 corrects only that rule, selects
`distributed_hp_damping_ks1_kc0p5_alpha0p6`, executes the held-out bank
(probe cross 0.79x local, guards and no-harm pass), but differential energy
reaches only 0.962x local versus 0.95 — `STOP-NO-DIFFERENTIAL-BENEFIT`
(`CLM-1035`).

Gate B-3 (`working/gate_b3_deterministic_physical_contract.md`, `CLM-1040`):
spectral diagnosis of R378 records shows the dominant differential mode at
0.4 Hz with the R378 alpha-0.60 corner on the mode; the successor freezes
alpha 0.90 (corner ~0.084 Hz, ~4.8x below the mode). R379 keeps identity on
all 60 development trajectories, best candidate reaches 0.914x local
differential energy, but every candidate exceeds the probe cross no-harm
ceiling (1.15-1.29x local vs 1.10) — `STOP-DEVELOPMENT-NO-CANDIDATE`.
Jointly R376-R379 evidence the first-order damping no-differential-benefit
boundary: a first-order frequency-selective channel cannot pass the 0.4 Hz
oscillation and reject the sustained action-domain probe within the frozen
0.95/1.10 thresholds. No filter-order sweep, gain change, retry, random arm,
headroom gate, or MARL.

R380 tests the next registered mechanism, a current-object full-order source
model with four separate VSG control inputs and three physical load inputs at
two fixed operating points (`CLM-1045`). Both source constructions and all
trajectory guards pass, but every sealed single-control record fails the
frozen fidelity limits. The route stops `STOP-MODEL-FIDELITY` before controller
design. It provides no authority for model changes, higher-order control,
physical comparison, retry, headroom, or MARL.

R381 tests one separately registered higher-order mechanism after a single-point
offline gate: a fixed two-stage washout neighbour controller on the same four
feasibility-native VSG node actions (`CLM-1050`). All 30 development trajectories
and guards are valid and the candidate reduces the differential-energy endpoint,
but it ties local settling and violates both probe-cross no-harm ceilings. R381
therefore stops `STOP-DEVELOPMENT-NO-CANDIDATE` without touching the evaluation
bank. No order/corner/gain change, retry, headroom test, or MARL is authorized.

R382 then tests a genuinely different premise (`CLM-1055`): whether a bounded,
outcome-seeing, non-causal residual family can witness joint headroom on the
same four VSG power ports without reopening R381. All 40 new trajectories and
physical guards pass. The privileged selector reduces disturbance differential
energy to 0.818x local, but every probe-coordinate selection falls back to the
local baseline, so both probe-cross ratios remain 1.0 instead of the required
0.95. R382 stops `STOP-NO-DETECTED-JOINT-HEADROOM` before the information or
training gates. The 0.818 result is disturbance-only authority, not title-level
decoupling evidence or a global headroom bound.

Next eligible action: close the experiment side and finish the manuscript
around the accumulated bounded negative evidence. The fixed title is not
supported by this line's results and remains a rejected target, not wording
that may be asserted in the abstract or contributions. Another controller,
filter/model revision, larger oracle family, information proxy, or learner is
not eligible on this route.

The learning comparison is terminally `BLOCK` on this route because the joint
non-learning headroom prerequisite did not pass. Information, capacity,
training/tuning, seed/checkpoint, and evaluation budgets must not be populated
to bypass that stop. The direct M/D stop remains; old storage, edge-agent,
common-channel, and R375 guard-failed outcomes are design inputs, not title
evidence.

## Reuse matrix

### Direct candidate reuse after the object/port gate

| Asset | Reuse | Required revalidation |
|---|---|---|
| `andes_vsg_env_v4.py` | Four-unit modified-Kundur builder, per-VSG state identity. | Expose VSG-owned power-reference seam; runtime M/D mutation stays stopped. |
| `active_power.py` | Energy, SOC, power, ramp, capability projection, anti-windup. | Rebind accounting to VSG-owned port and achieved power; no ESD1 semantics. |
| `andes_vsg_storage_env.py` | Bus placement, ESD1 checks, telemetry, constraint plumbing. | Implementation donor only; GFL ESD1 devices are not the acting object. |
| `v4_config.py` | Paper-strict and modified reward/action configs. | Freeze one new-line config; no old composite inheritance. |
| `agents/sac.py` | Independent per-agent SAC. | Prove separate parameters, replay, action output, reset, save/load, deterministic eval. |
| `agents/sac_ctde.py` | Optional CTDE scaffold. | Runtime observations/actions per-VSG; compare vs independent SAC. |
| `feasibility_native_vsg_action.py` | Four-node seam: one normalized scalar per VSG to its physical interval. | Qualify offline, then identity at the unchanged VSG port in a new physical gate. |
| training and sealed-bank adapters | Execution, seeding, checkpoint, provenance, failure retention. | New hashes, seeds, banks, budgets; no old checkpoint dependence. |

### Adaptable methodology, not drop-in scientific evidence

| Asset family | Useful part | Boundary |
|---|---|---|
| `decentralized_dapi.py`, relative-RoCoF, coupling-aware, model-first controls | Deterministic coordination candidates, common/differential analysis. | Retune to the VSG-owned power port under matched information/action permissions. |
| headroom, projection, storage, fallback mechanisms | Bounded direct actions, energy feasibility, no-harm, residual ablations. | Rebind to the VSG-owned power port; old feasibility numbers do not transfer. |
| `physical_endpoints.py`, `sealed_bank.py`, `eval_v2.py`, integrity tools | Physical endpoints, paired evaluation, provenance, failure handling. | New preregistered decoupling endpoints replace the old headline composite. |
| R338 distributed execution, R359-R363 model-first implementations | Failure patterns, locality tests, action projection, probe design. | Scalar/edge/common-channel objects and outcomes are not the new per-VSG object. |

### Reference only

- `C:/Users/27443/Desktop/Multi-Agent  VSGs/docs/paper/yang2023-fact-base.md`
  — verified paper facts and known ambiguities.
- `C:/Users/27443/Desktop/Decoupling-Oriented_Coordination_of_Paralleled_VSGs_with_MARL_deep-research.md`
  — decoupling taxonomy, strong-baseline logic, ablations, evidence ladder.
- The old Simulink repository is a reproduction oracle only; ANDES is the
  sole canonical simulation platform.

### Never transfer

- old checkpoints, training curves, result values, paper claims, or title
  language;
- the six-axis legacy composite as a primary endpoint;
- scalar area actions or three edge actors as per-VSG agents;
- common-channel feasibility as a controller or MARL gain;
- fixed-topology results as topology generalisation;
- a numerical match to undisclosed Simulink settings.

## Phase sequence

### Phase 0 — VSG-owned energy-port object

Keep the four validated VSG identities from `CLM-0975`; replace the stopped
M/D actuator with one VSG-owned active-power-reference port per unit.
`CLM-1000` passes the static source/implementation contract; `CLM-1005`
passes the finite real-environment object gate (sign, timing, zero-action
behavior, independent intervention, electrical response, achieved-power
incremental energy settlement). Exact Yang trajectories, reward numbers, and
M/D action ranges are not targets.

### Phase 1 — Strong deterministic power coordination

Four feasibility-native node actions on the same four per-VSG
power-reference ports. Each deterministic actor outputs one normalized local
action; the distributed arm uses frozen neighbour messages, the local arm
does not. Both pass the same per-node map from `[-1,1]` to the current
power/ramp/capability/SOC/energy interval; the outer projection must be
identity. Freeze identical coordinates, limits, update rate, accounting,
development/holdout banks, and tuning budget for all later methods.

Decoupling co-primary endpoints: off-diagonal signed-response energy on a
fresh probe bank and disturbance-driven differential-frequency energy on a
separate disturbance bank. Settling/dispersion, common frequency, worst-unit
peak, RoCoF, control effort/energy, projection leakage, saturation, bound
contact, and failures are secondary or no-harm.

Proceed only if the object has nonzero bounded direct power authority and
the permission-matched deterministic benchmark passes every physical guard
while leaving a falsifiable learning question. R375 stops the first frozen
controller formulation at this boundary. Any separately justified successor
must pass a new prospective deterministic gate, after which a bounded
non-learning time-varying action oracle must show incremental headroom
beyond that deterministic controller with nonconstant, coordination-
dependent action targets.

### Phase 2 — Direct per-VSG power-reference MARL

Each VSG actor outputs its own normalized feasible active-power action
through the object-gated energy port. Minimum comparison set: zero feasible
action, local and neighbour deterministic control, random bounded direct
action, independent RL, MARL without messages, MARL with messages, and a
decoupling-objective ablation. All arms use the same four node actions and
feasibility map. A centralized four-action optimizer may serve as oracle or
comparator, never as the runtime multi-agent object.

The title passes only if message-enabled MARL beats the strongest
permission-matched non-learning method on preregistered physical endpoints
without more failures or control stress. A no-message ablation and a
decoupling-objective ablation must attribute any increment to runtime
coordination and cross-coordinate suppression rather than policy capacity
alone. Otherwise report a bounded negative result and stop algorithm
variants.
