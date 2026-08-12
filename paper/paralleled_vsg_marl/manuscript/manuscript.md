# Decoupling-Oriented Coordination of Paralleled VSGs With Multi-Agent Reinforcement Learning

**Status note (not for submission):** this working title is fixed by
repository policy but is an *unsupported target* on the evidence below. Every
title term remains prospective; the manuscript reports a bounded negative
result and must not be read as supporting MARL, coordination, or positive
decoupling claims. Draft is venue-neutral (venue unassessed).

## Abstract

Multi-agent reinforcement learning (MARL) is frequently proposed to coordinate
parallelled virtual synchronous generators (VSGs) toward decoupling-oriented
operation, yet almost all such comparisons are made against fixed-droop or
no-control baselines under unmatched action permissions, without energy
feasibility, and without a headroom gate before training. This paper reports a
preregistered, gate-based study on one common object: four VSG units of a
modified Kundur two-area system, each owning an independently intervenable,
energy-constrained active-power-reference port, evaluated with matched
zero/local/neighbour deterministic baselines, physical guard-first validity,
and an outcome-blind non-learning headroom oracle.

The object and actuator prerequisites pass: four VSG-owned ports are validated
with zero-action equivalence, independent intervention, signed achieved-power
authority in the common and three differential coordinates, and consistent
energy accounting [CLM-0975, CLM-1000, CLM-1005, CLM-1010]. The control chain
does not. A frozen local-neighbour M/D controller showed development-bank
efficacy, but the non-deployable conditional oracle added only about 1.05%
beyond it, below the frozen 5% gate, stopping the direct M/D formulation
[CLM-0990]. The deterministic power-reference formulation stopped when every
held-out trajectory of its selected controller triggered the energy-port
ramp-projection guard [CLM-1020]. First-order frequency-selective damping
channels cannot jointly pass the 0.4-Hz differential oscillation and reject
the sustained action-domain probe within the frozen 0.95/1.10 thresholds
[CLM-1025, CLM-1030, CLM-1035, CLM-1040]; a full-order source-model route
failed trajectory fidelity before controller design [CLM-1045]; a two-stage
washout controller violated both probe-cross no-harm ceilings [CLM-1050]; and
even a bounded, outcome-seeing, non-causal residual family reduced only the
disturbance differential endpoint (0.818x local) while every probe-coordinate
selection fell back to the local baseline, so no joint decoupling headroom was
witnessed [CLM-1055]. The joint non-learning headroom prerequisite therefore
never passed, and the direct per-VSG MARL comparison is terminally blocked on
this route [ROUTE.md]. We report the accumulated bounded negative evidence, the
protocol that produced it, and the explicit boundaries of what it does not
prove.

*Keywords:* virtual synchronous generator, parallelled VSG coordination,
multi-agent reinforcement learning readiness, active-power-reference control,
preregistered negative result

## 1. Introduction

Parallelled VSGs are expected to share active power and support frequency
while remaining mutually coupled through the common network. Heterogeneous
inertia and damping and localized disturbances create inter-unit differential
oscillation, and a family of works proposes to coordinate the units — by
adapting per-unit inertia/damping parameters or by commanding per-unit
power references — sometimes with learning-based agents (e.g., the per-VSG
inertia/droop coordination object of Yang et al., DOI
10.1109/TPWRS.2022.3221439). The difficulty in assessing these claims is
methodological rather than algorithmic: reported learned gains are typically
measured against fixed droop or zero control, with different action bounds,
information, update timing, and energy feasibility from the baseline, and
training starts before anyone checks whether a strong deterministic
coordinator already absorbs the attainable improvement.

This study therefore asks one falsifiable question on a single common object:
does direct per-VSG coordination add value over a matched strong deterministic
baseline, without physical, energy, or control-stress harm, and is there enough
non-learning headroom that a learning question even exists? We answer it with a
preregistered sequence of gates: (i) object and actuator validation; (ii)
matched deterministic physical comparisons with guard-first validity; (iii) an
outcome-blind headroom oracle before any training eligibility. The contribution
is bounded and negative:

- Four VSG-owned, energy-constrained active-power-reference ports are
  validated on one plant: the four-VSG object identity and per-actor
  intervention premise [CLM-0975], the port design with zero-action
  equivalence, independent signed intervention, achieved-power energy
  accounting [CLM-1000, CLM-1005], and nonzero cross-coordinate response
  [CLM-1010].
- Five registered control mechanisms stop at preregistered gates: direct M/D
  (no conditional headroom), deterministic power-reference (projection
  saturation), first-order damping family (joint 0.95/1.10 thresholds
  unsatisfiable), full-order source model (trajectory fidelity), and two-stage
  washout (probe-cross ceilings) [CLM-0990, CLM-1020, CLM-1025, CLM-1030,
  CLM-1035, CLM-1040, CLM-1045, CLM-1050].
- A bounded, outcome-seeing, non-causal residual family separates
  disturbance-only authority (0.818x local differential energy) from joint
  decoupling headroom, which is absent on every probe coordinate [CLM-1055].
- Because the joint non-learning headroom prerequisite never passed, the
  direct per-VSG MARL comparison is terminally blocked; the fixed title terms
  remain unsupported targets [ROUTE.md].

The remainder of the paper: system model and per-VSG energy port (Section 2),
the matched comparison protocol (Section 3), results (Section 4), discussion
(Section 5), related work (Section 6), and conclusion (Section 7).

## 2. System model and the VSG-owned energy port

### 2.1 Plant and object identity

The object is an electromechanical proxy on the ANDES platform: a modified
Kundur two-area four-machine system in which four GENCLS units are added as
VSG proxies at buses 12, 16, 14, and 15 and are ordered as `VSG_1..VSG_4`.
The physical frequency base is 60 Hz; the legacy observation normalization
uses a 50-Hz constant, and the comparison contract converts only the six
frequency/RoCoF slots by the ratio 60/50 so that all physical endpoints are
reported in 60-Hz units [CLM-0975, CLM-0980]. The four units are governor-free:
installed ANDES source inspection confirms that IEEEG1 governors attach only
to the GENROU devices and not to the added GENCLS VSG proxies, and the
governor-free algebraic equation enforces `tm0 - tm = 0` [CLM-1000].

On this plant the registered per-VSG object gate passes: each of the four
units maps one-to-one to one runtime actor; the eight normalized
actor-channel coordinates have rank-eight executed M/D readback; the seven
per-VSG observation fields reconstruct from the same-step local and declared
ring-neighbour signals (maximum absolute error ~3e-8) with zero delay and
zero dropout, i.e., no communication failure for this study [CLM-0975]; the
combined heterogeneous-damping and localized-load-step condition produces an
above-noise differential transient; and each actor's bounded intervention
changes at least one other VSG frequency or active-power trace above the
repeated-run numerical floor [CLM-0975]. This is an existence/interface
result on one topology, one disturbance, and one six-second horizon; it
establishes no controller efficacy by itself.

### 2.2 The energy-constrained active-power-reference port

The successor actuator (after the direct M/D formulation stopped) is one
bounded active-power-reference port owned by each VSG unit, backed by an
explicit energy state [CLM-0995]. Each actor requests an incremental
active-power quantity on the 100-MVA system power base; the wrapper writes
one absolute `SynGen.pref` value per VSG, sends exact zero actions through
the stopped legacy M/D path, and does not instantiate or act on any
independent storage device [CLM-1000, CLM-1010]. At each sample, the projected system-base power increment
is converted to mechanical torque as `p_cmd / omega_sample` before being added
to the baseline `tm0`; after the hold, both the setpoint and the actual
`GENCLS.tm` are recorded, and achieved incremental power and state of charge
are settled from actual torque times the trapezoidal endpoint speed — not from
the requested, commanded, or setpoint power [CLM-1000]. The source-traceable
power, ramp, current-capability, SOC, and energy projection is reused only as
a per-device feasibility envelope; the outer projection is an identity guard
and any external saturation is a hard invalidity, not an accepted control
event [CLM-1020, feasibility-native contract]. In the authority bank the
registered actuator bounds are a maximum signed command of 0.04 system p.u., a
maximum slew of 0.2 system p.u./s, and an SOC envelope of 0.4997-0.5003 with
zero saturation and zero charge/discharge recomputation error [CLM-1010].

The physical object gate then passes on one deterministic, no-disturbance,
one-second gate: wrapped zero power is trajectory-equivalent to unchanged V4
under a 1e-9 tolerance; all eight signed 0.04-system-pu single-port
interventions preserve the ordered identity, change only their named request,
setpoint, torque residual, and energy state, and produce target electrical
responses of 0.0487-0.0513 system pu; the independently recomputed charge,
discharge, and SOC ledger matches telemetry [CLM-1005]. A bounded
three-condition authority bank extends this: across 12 condition-mode cells,
the minimum signed projected achieved power is 0.0400 system pu, diagonal
frequency-response RMS spans 0.00159-0.00771 Hz, diagonal electrical-response
RMS spans 0.0263-0.0421 system pu, and the finite response matrices retain
nonzero cross-coordinate terms — for the Bus-14 inter-area cell the
descriptive diagonal-to-largest-cross frequency ratio is 1.71 [CLM-1010].
Nonzero off-diagonal responses are the decoupling problem: coordinate
relabelling alone is not decoupling evidence.

## 3. Matched comparison protocol

### 3.1 Arms and permissions

Every comparison arm uses the same four per-VSG node-action coordinates, the
same feasibility map, actuator path, physical limits, update timing (0.2 s),
seed (42), development and held-out banks, and failure accounting. The arm set
is: zero feasible action; local feasibility-native deterministic control;
neighbour deterministic control (frozen ring messages); bounded random
residual; independent RL; no-message MARL; message-enabled MARL; and a
decoupling-objective ablation, with a centralized vector oracle as a
nondeployable upper reference [feasibility-native contract]. A normalized
residual `r_i in [-1,1]` maps into the deterministic anchor's remaining
feasible headroom: `r_i=0` restores the anchor exactly, `r_i=+/-1` reaches the
current bounds, and malformed residuals or infeasible baselines fail closed.
No central process pools actor outputs into a scalar or edge action.

### 3.2 Endpoints and thresholds

`Decoupling-Oriented` is an input-output property, not a coordinate name. The
frequency coordinates are arithmetic projections of the four VSG rotor speeds
into one common and three zero-sum differential coordinates. The joint
evidence requires (i) lower off-diagonal common/differential signed-response
energy on a fresh paired probe bank; (ii) lower disturbance-driven
differential-frequency energy and settling; (iii) no material degradation of
common frequency, worst-unit peak, RoCoF, failures, saturation, energy, or
control stress. Frozen decision thresholds used in this study: primary
differential-energy ratio at most 0.95x local; probe cross no-harm ceilings at
1.10 and 1.05 common-IAE ceiling (frozen from R376 onward); non-learning
headroom gate at 5% incremental improvement over the strongest valid
deterministic controller [CLM-0980, CLM-0990, R376-R382 contracts].

### 3.3 Validity and stop rules

All analyses are guard-first: physical/execution guards (identity, timing,
finiteness, power/ramp/energy/SOC, saturation, bound contact, zero legacy M/D)
take precedence over every performance endpoint. Development selection happens
only on immutable development records; a held-out bank is instantiated only
after a valid development selection; the evaluation bank is conditionally
accessible. Formal stops are terminal: `STOP-UNSAFE-CONTROL`,
`STOP-NO-DIFFERENTIAL-BENEFIT`, `STOP-DEVELOPMENT-NO-CANDIDATE`,
`STOP-MODEL-FIDELITY`, `STOP-NO-CONDITIONAL-HEADROOM`,
`STOP-NO-DETECTED-JOINT-HEADROOM` each forbid retry, gain/order/corner
changes, headroom tests, and training [CLM-0985, CLM-1020, CLM-1045,
CLM-1050, CLM-1055]. Two intermediate analyses were invalid under their own
rules and were corrected outcome-blind without retry: R368's actuator-mapping
tolerance was repaired with the binary32 half-ULP bound (2^-15), and R374's
classifier identity contract was aligned to the runtime `VSG_1..VSG_4`
[CLM-0985, CLM-1015, CLM-0990].

## 4. Results

### 4.1 Direct per-VSG M/D formulation: no conditional headroom

On the immutable complete R368 development bank, the outcome-blind correction
made all 80 mapping checks pass and the unchanged classifier selected the
fixed local-neighbour controller `local_neighbour_md_km1_kd2`, whose aggregate
differential-frequency energy is 69.92% lower than zero action with every
completion, common-frequency, saturation, bound, and slew guard passing
[CLM-0990]. The non-deployable per-scenario best-of-nine oracle then added
only 1.046% over that fixed controller — below the frozen 5% headroom
threshold — with nonconstant traces selecting two distinct candidate names.
The typed result is `STOP-NO-CONDITIONAL-HEADROOM`, closing the registered
direct per-VSG M/D learning formulation without training or sweep. This
rejects only that finite pretraining screen, not MARL as a class [CLM-0990].

### 4.2 Deterministic power-reference formulation: projection saturation

After the actuator moved to the VSG-owned power-reference port, the frozen
deterministic cross-coordinate decoupling comparison selected
`distributed_ks1_kc0p5` on corrected immutable development records (R375
aligned the classifier identity contract of R374 to `VSG_1..VSG_4`)
[CLM-1015, CLM-1020]. All 30 newly sealed held-out trajectories completed
without TDS failure or training; cross-coordinate, differential-motion,
settling, and common-mode comparisons were descriptive-passing — but every one
of the selected controller's ten held-out trajectories triggered the
energy-port ramp-projection guard (15 saturated steps labelled `ramp` across
the bank). Guard precedence therefore blocks deterministic decoupling
efficacy, safe coordination, non-learning headroom, and MARL training; the
formulation stops `STOP-UNSAFE-CONTROL` [CLM-1020]. The directional endpoint
reductions in the failed-guard diagnostics (off-diagonal response energy
0.11-0.57x, differential energy 0.32-0.72x of baselines) are not evidence of
efficacy; they are retained only as the stop record.

### 4.3 First-order frequency-selective damping family

Four registered comparisons map the boundary of the first-order damping law
family on the same feasibility-native four-VSG node actions. R376: the local
feasibility-native controller descriptively reduced the registered endpoints
versus zero feedback, but none of the four frozen distributed gain pairs
cleared the development eligibility rule (probe off-diagonal ratios 1.12-1.18
and normalized cross ratios 1.12-1.19 versus the 0.98 threshold) —
`STOP-DEVELOPMENT-NO-CANDIDATE` [CLM-1025]. R377 stopped on an unsatisfiable
settling-floor rule artifact (every arm already at the 1.2-s floor; the frozen
rule demanded one 0.2-s step of improvement), a contract defect corrected
outcome-blind by R378 [CLM-1030]. R378 executed the 30-record held-out bank
for the corrected high-pass candidate: probe cross-response fell to 0.79x
local (no-harm ceiling passes) but mean differential-frequency energy reached
only 0.962x local versus the required 0.95 — `STOP-NO-DIFFERENTIAL-BENEFIT`
[CLM-1035]. R379 moved the corner to ~0.084 Hz (alpha 0.90, ~4.8x below the
0.4-Hz differential-oscillation frequency measured on this plant's records):
the best candidate reached 0.914x local differential
energy, but every candidate exceeded the probe-cross no-harm ceiling
(1.15-1.29x vs the 1.10 limit) — `STOP-DEVELOPMENT-NO-CANDIDATE` [CLM-1040].
Jointly, R376-R379 demonstrate the registered no-differential-benefit boundary:
a first-order frequency-selective channel cannot simultaneously pass the
0.4-Hz differential oscillation and reject the sustained action-domain probe
within the frozen 0.95/1.10 thresholds on this plant [CLM-1040].

### 4.4 Full-order source-model route: trajectory fidelity

R380 separately constructed full-order four-VSG control and physical-load
source models at two fixed operating points. Both constructions passed every
frozen source guard (object validity, finite-difference convergence and
symmetry, descriptor conditioning, named-state alignment, separate control and
disturbance matrices, full control-channel rank), and all 36 registered
nonlinear trajectories completed with every hard guard true and zero-repeat
maximum 0.0 Hz. Nevertheless all 16 single-control records failed the frozen
trajectory-fidelity limits: maximum control-record NRMSE 1.139 versus 0.15 and
maximum peak vector residual 0.969 versus 0.20. The route terminates
`STOP-MODEL-FIDELITY` before controller design; source/Jacobian agreement and
input-channel rank do not transfer to sampled nonlinear trajectory fidelity on
this object [CLM-1045].

### 4.5 Two-stage washout neighbour controller

R381 tested one fixed second-order neighbour controller (two identical
washouts in series on the Laplacian frequency message, 0.05-Hz corner) with
zero/local baselines on the same four feasibility-native VSG ports. All 30
development trajectories pass every physical/execution guard with probed
action rank four, zero outer-projection distortion, no bound contact, and no
energy saturation. The candidate reduces mean differential-frequency energy to
0.917x local but ties the local 1.3-s settling and raises probe off-diagonal
energy and normalized cross ratio to 1.289x and 1.301x of local, above the
frozen 1.10 ceilings; the common-IAE ratio (0.9998x) cannot override the
failing checks. `STOP-DEVELOPMENT-NO-CANDIDATE` without inspection of the
evaluation bank [CLM-1050]. The comparison identifies this complete fixed
controller instantiation rather than filter order, communication, or the
distributed-control class as an isolated causal factor.

### 4.6 Outcome-seeing headroom witness: disturbance-only authority

R382 asked the sharpest question of the chain: can a bounded, outcome-seeing,
non-causal residual family witness joint decoupling headroom on the same four
power ports, without reopening any stopped mechanism? All 40 registered
trajectories complete with every identity, timing, power/ramp/energy/SOC,
zero-sum residual, projection, saturation, and legacy-M/D guard passing. The
finite-family per-condition oracle lowers mean disturbance differential-
frequency energy from 3.867e-4 to 3.165e-4 Hz^2*s (ratio 0.818, 18.2% lower)
with unchanged 1.3-s settling and no registered endpoint harm — but for every
one of the four registered probe coordinates the constrained selector returns
the unchanged local baseline, leaving both aggregate probe-cross ratios at
exactly 1.0 versus local instead of the required 0.95. The terminal
classification is `STOP-NO-DETECTED-JOINT-HEADROOM`, before any local-
information test or training [CLM-1055]. The 0.818 result is disturbance-only
control authority; it is not a global optimum, an impossibility result, or
evidence about all neural/MARL formulations.

### 4.7 Chain summary

Table 1 collects the object/actuator validation; Table 2 collects the gate
sequence. The joint non-learning headroom prerequisite never passed at any
point in the chain; the direct per-VSG MARL comparison is therefore terminally
blocked on this route, and the fixed title terms remain unsupported targets
[ROUTE.md].

**Table 1 — Object and actuator validation.**

| Gate | Bank | Outcome | Bound |
|---|---|---|---|
| Per-VSG object (R365) | 8 arms x 30 decisions | PASS; rank-8 readback, 7-field reconstruction, differential transient, cross-unit authority | one topology, one disturbance, 6 s |
| Energy-port design (R371) | static source contract | PASS; pref/tm seam, achieved-power energy settlement | no trajectory |
| Physical object (R372) | 10 arms x 5 decisions | PASS; zero-action equivalence 1e-9, signed 0.04-pu responses 0.049-0.051 pu, ledger match | one point, no disturbance, 1 s |
| Bounded authority (R373) | 3 conditions x 10 arms x 40 decisions | PASS; common+3-differential authority, nonzero cross terms | one topology, 8 s |

**Table 2 — Control gate sequence (all terminal stops).**

| Mechanism | Evidence | Terminal stop | Headline number |
|---|---|---|---|
| Direct per-VSG M/D (R369) | development bank | STOP-NO-CONDITIONAL-HEADROOM | oracle +1.05% < 5% |
| Deterministic power-reference (R375) | 30 held-out trajectories | STOP-UNSAFE-CONTROL | 10/10 trajectories saturated |
| First-order damping family (R376-R379) | 4 comparisons | NO-DIFFERENTIAL-BENEFIT / NO-CANDIDATE | 0.962x vs 0.95; probe 1.15-1.29 vs 1.10 |
| Full-order source model (R380) | 2 points, 36 records | STOP-MODEL-FIDELITY | NRMSE 1.139 vs 0.15 |
| Two-stage washout (R381) | 30 development trajectories | STOP-DEVELOPMENT-NO-CANDIDATE | probe 1.289/1.301 vs 1.10 |
| Outcome-seeing residual (R382) | 40 trajectories | STOP-NO-DETECTED-JOINT-HEADROOM | disturbance 0.818x; probe 1.0 vs 0.95 |

## 5. Discussion

Three mechanisms consistently explain the accumulated negative evidence, and
each is bounded to this plant and protocol.

*Disturbance authority is not joint decoupling authority.* Across the whole
chain, no mechanism passed the registered joint gate; the largest witnessed
disturbance-endpoint improvement against the strongest matched local baseline
is R382's 18.2% reduction of disturbance-driven differential-frequency energy
under a result-privileged, non-deployable selector. That same selector could
not improve a single probe coordinate; the two aggregate probe-cross measures
stayed exactly at the local baseline. The registered protocol therefore
separates what a controller can do for one endpoint from what the title's
decoupling objective requires — a coordinated suppression of cross-coordinate
response that no tested mechanism produced. This separation is itself the main
methodological output.

*First-order selectivity cannot serve both endpoints on this plant.* The
measured differential-oscillation frequency of this plant sits near 0.4 Hz,
and the sustained action-domain probe occupies the action band. R376-R379 show
that a first-order frequency-selective channel either passes the oscillation
while amplifying the probe (R379, probe 1.15-1.29x) or rejects the probe while
missing the threshold on
the oscillation (R378, 0.962x vs 0.95). The two-stage washout, a genuinely
higher-order mechanism, also failed both probe-cross ceilings while tying
settling [CLM-1050]. This is negative evidence for the tested law families on
this object, not a theorem about all filters or all plants.

*Energy feasibility is a hard constraint, not a post-processing step.* R375's
selected controller was descriptively promising and physically saturated on
every held-out trajectory at the energy-port ramp projection [CLM-1020]. The
feasibility-native successor fixed this structurally — the residual spans only
the anchor's remaining headroom and the outer projection is an identity guard
— but by then the deterministic candidates themselves could not pass the joint
thresholds. The protocol treated saturation as invalid, which is the
precondition for any honest learning comparison.

*What the negative evidence does not prove.* Nothing here is an impossibility
result, a bound over all feasible time-varying controls, or evidence that all
neural policies or MARL formulations lack value [CLM-1055, CLM-0990]. The
evidence covers one modified-Kundur topology, deterministic small-pulse and
load-step banks, finite development/holdout trajectories, one seed, a GENCLS
electromechanical actuator without converter inner loops, and no unseen
operating conditions or topologies. In particular, the outcome-seeing witness
is deliberately nondeployable and information-advantaged; its failure is
therefore a strong headroom screen, not a deployability result.

*Implications for the field.* The practical lesson is that matched permissions
and a headroom gate change the interpretation of learned coordination: on this
object, a strong deterministic anchor absorbs essentially all measurable
joint improvement, and the remaining disturbance-only margin is exactly what a
reward-driven learner would chase — with no evidence that it transfers to the
decoupling objective. Comparable studies should report (i) the actuator's
energy feasibility behavior, (ii) probe cross-response alongside
disturbance endpoints, and (iii) a non-learning headroom oracle before
training, or their learned-gain claims remain comparison-contract artifacts.

## 6. Related work

VSG coordination. Per-unit inertia/droop adaptation is the dominant action
family for multi-VSG coordination; Yang et al. (DOI 10.1109/TPWRS.2022.3221439)
is the object and algorithm reference for the per-VSG information pattern used
here (advisory context; numerical settings of that study are not disclosed in
the cited report and no exact numerical reproduction is claimed).
Active-power/frequency-reference control and distributed secondary control of
parallelled grid-forming converters form the adjacent family that motivates
the energy-constrained power-reference actuator of this study; existing
implementations of per-device power, ramp, current, SOC, and energy projection
informed the feasibility envelope reused here.

MARL for power control. Several studies train independent or shared-policy
agents for frequency/voltage control, often against fixed-droop or
no-control baselines. The evidence base is heterogeneous in action
permissions, information patterns, and evaluation banks; direct multi-VSG
MARL with one runtime actor per unit and matched permissions is comparatively
sparse. This study contributes no positive result to that evidence base; its
positioning is that such comparisons are uninformative without the matched
baseline and headroom protocol of Section 3.

Learning readiness and headroom gates. Theoretical work on controllability and
performance-difference bounds, residual-learning experiments, and
information-value analysis jointly support the view that after a strong
classical controller occupies the dominant modes, the remaining residual
problem can be small, low-signal, and weakly information-dependent. Our
results instantiate that view on one concrete power system object: the
outcome-seeing oracle found headroom only on the disturbance endpoint and none
on the joint probe objective. We do not claim that no trainable increment
exists anywhere; we report that none was witnessed on this object under this
protocol, and that the registered gates consequently blocked training.

## 7. Conclusion

On one modified-Kundur object with four VSG-owned, energy-constrained
active-power-reference ports and a permission-matched, guard-first protocol,
the registered evidence is bounded and negative. The object and actuator are
valid; five control mechanisms stop at preregistered gates; and a privileged
outcome-seeing oracle separates disturbance-only authority from the joint
decoupling headroom that the fixed title's `Decoupling-Oriented` term
requires. Because the joint non-learning headroom prerequisite never passed,
the direct per-VSG MARL comparison is terminally blocked on this route, and
the fixed title terms — paralleled VSGs (object premise only), decoupling-
oriented, coordination, and MARL — remain unsupported targets. We report this
negative evidence together with the protocol that produced it, in the
expectation that permission-matched, headroom-gated evaluation becomes the
standard precondition for learned coordination claims in parallelled VSG
systems.

## Limitations

- One modified-Kundur topology, finite deterministic banks, one seed, one
  update rate; no population, uncertainty, robustness, or held-out operating
  conditions beyond the registered banks.
- The actuator is a governor-free GENCLS `pref/tm` electromechanical seam with
  an external incremental energy ledger; converter inner loops, DC-link,
  switching, reactive power, thermal behavior, protection, and hardware are
  unmodeled.
- Frequency coordinates are arithmetic projections of four rotor speeds, not
  COI frequency, bus estimators, or a small-signal modal certificate.
- All negative results are bounded to the tested law families, information
  patterns, and banks; they are not impossibility, stability, safety,
  robustness, topology-generalization, or deployment results.
- Deep-research and survey documents consulted for framing are advisory
  context; no experimental claim in this paper depends on them.

## References (advisory; verify before submission)

1. Yang et al., multi-VSG coordination reference, IEEE TPWRS, DOI
   10.1109/TPWRS.2022.3221439.
2. Repository evidence chain: claims CLM-0975..CLM-1055 and feeds
   paper/paralleled_vsg_marl/reports/R364..R382 (canonical locators in the
   claim registry).
