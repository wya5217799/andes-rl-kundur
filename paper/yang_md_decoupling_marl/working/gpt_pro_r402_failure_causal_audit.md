# GPT Pro Problem Package: Causal Audit of the R402 MARL Canary Failure

## Status and intended use

- **Paper title (must remain unchanged):** *Decoupling-Oriented Coordination of Paralleled  VSGs With Multi-Agent Reinforcement Learning*
- **Target venue:** ICEMS 2026 conference paper.
- **Question type:** causal-identifiability, optimization-diagnosis, and model-boundary audit.
- **Evidence status:** the numerical experiment results below are repository evidence only where explicitly tied to R399, R402, R408, or R409. The post-hoc forensic quantities are diagnostic analyses of sealed data, not prospectively registered causal findings.
- **Authority boundary:** do not recommend retraining, changing an algorithm, reopening a consumed bank, or promoting a mathematical derivation into experimental evidence. First determine what can and cannot be inferred from the existing record.
- **Desired language:** the analysis may be written in Chinese, but all proposed manuscript sentences must be submission-quality English.

This document asks for an independent audit. Do not assume that the causal interpretation currently suggested by the authors is correct. Recompute the logic from the facts, expose contradictions, and use the weakest claim that remains valid.

## 1. Primary research question

> Given a fixed three-arm, three-seed direct-inertia/direct-damping MARL canary whose learned policies fail all physical guards and underperform a strong deterministic controller, which candidate failure mechanisms are mechanically established, empirically supported, merely plausible, contradicted, or unidentifiable from the available logs and experiments?

### Sub-questions

1. Did the projected Lagrange-multiplier design materially remove the common-mode objective during training, and what can that fact explain?
2. To what extent can missing action-effort regularization explain action stress, common-mode degradation, and the two decoupling-endpoint failures?
3. Can insufficient optimization, runtime-message redundancy, partial observability, or direct-M/D actuator limitations be distinguished without a corrected prospective experiment?
4. What is the minimum additional evidence required for each stronger causal statement?
5. What wording is safe for the current conference paper without overstating a cause?

## 2. System and experimental object

### 2.1 Simulator and plant scope

- ANDES 2.0.0, positive-sequence phasor-domain differential-algebraic-equation simulation.
- One fixed-connectivity modified Kundur two-area topology.
- Four synchronous-machine proxies operated as four VSG proxies.
- Physical frequency endpoints use the installed 60-Hz base.
- Protected legacy controller observation slots use a 50-Hz scale and are converted once to the 60-Hz physical scale before the new controller consumes them.
- Controller update interval: 0.2 s.
- Each episode and each evaluation trajectory: 30 controller steps, corresponding to a 6-s post-disturbance window.
- No EMT, hardware-in-the-loop, field, arbitrary-topology, or global-stability evidence exists.

### 2.2 Common/differential coordinates

Let the four-device frequency-deviation vector be $\Delta f\in\mathbb R^4$. The arithmetic common coordinate is

\[
z_c=\frac14\mathbf 1^\top\Delta f.
\]

The registered three-row differential transform is

\[
T_d=
\begin{bmatrix}
1/2&1/2&-1/2&-1/2\\
1/\sqrt2&-1/\sqrt2&0&0\\
0&0&1/\sqrt2&-1/\sqrt2
\end{bmatrix}.
\]

The first row is an inter-area contrast; the other two are within-area contrasts. These are arithmetic evaluation coordinates, not identified nonlinear modes.

### 2.3 Direct-M/D action channel

Each of the four actors independently emits

\[
a_i=(a_i^M,a_i^D)\in[-1,1]^2.
\]

Each normalized component is decoded asymmetrically:

\[
\Delta q(a)=
\begin{cases}
600a,&a\ge0,\\
200a,&a<0,
\end{cases}
\]

and applied as

\[
M_i=\max\{20,M_{0,i}+\Delta q(a_i^M)\},\qquad
D_i=\max\{10,D_{0,i}+\Delta q(a_i^D)\}.
\]

The normalized componentwise slew limit is $0.25$ per update. This is parameter modulation, not direct active-power injection. The map is nonsmooth at zero and can also encounter the physical lower clamps.

## 3. Profile and disturbance bank

The bank contains four development profiles and four evaluation profiles. Every profile has six signed trajectories: positive/negative common probes, positive/negative differential probes, and positive/negative localized disturbances.

For a profile with probe magnitude $p$:

- common positive probe: $\Delta u=(p/4,p/4,p/4,p/4)$ across the four registered loads;
- differential positive probe: $\Delta u=(p/4,p/4,-p/4,-p/4)$;
- negative probes reverse the sign;
- localized probes apply $\pm\ell$ at the named location.

| Profile | Split | $M_0$ | $D_0$ | Steady loads $(P_{14},P_{15})$ | Probe $p$ | Localized location | $\ell$ |
|---|---|---|---|---:|---:|---|---:|
| canary_dev_a | development | [150, 250, 170, 230] | [60, 140, 80, 120] | (2.24, 0.42) | 0.85 | PQ_1 | 0.95 |
| canary_dev_b | development | [230, 150, 250, 170] | [120, 60, 140, 80] | (2.02, 0.66) | 1.05 | PQ_Bus15 | 1.15 |
| canary_dev_c | development | [210, 190, 160, 240] | [130, 70, 110, 90] | (2.42, 0.14) | 0.75 | PQ_0 | 0.85 |
| canary_dev_d | development | [240, 160, 190, 210] | [90, 110, 70, 130] | (2.12, 0.54) | 0.95 | PQ_Bus14 | 1.05 |
| canary_eval_a | evaluation | [140, 260, 200, 220] | [50, 150, 90, 130] | (2.56, 0.34) | 0.90 | PQ_0 | 1.00 |
| canary_eval_b | evaluation | [260, 140, 220, 200] | [150, 50, 130, 90] | (2.06, 0.26) | 0.80 | PQ_Bus14 | 0.90 |
| canary_eval_c | evaluation | [180, 240, 150, 210] | [70, 130, 60, 110] | (1.96, 0.64) | 1.00 | PQ_Bus15 | 1.10 |
| canary_eval_d | evaluation | [220, 200, 260, 140] | [110, 90, 150, 50] | (2.32, 0.46) | 1.10 | PQ_1 | 1.20 |

The four development profiles are used in the training schedule. The four evaluation profiles are not used for training or checkpoint selection.

## 4. Controllers and learning contract

### 4.1 Strong deterministic reference

The reference is `local_neighbour_md_km2_kd2`, selected on a separate deterministic development protocol from a finite bank of nine local-neighbour M/D laws. In R399:

- relative to zero action on two development profiles, it reduces aggregate signed off-diagonal response energy by 60.79%;
- it reduces disturbance differential-frequency energy by 64.13%;
- every registered development guard passes;
- an outcome-seeing oracle restricted to the same nine-law family selects this same law on all four R399 evaluation profiles and obtains 0% additional improvement on both endpoints.

This establishes a strong finite-family comparator. It does **not** prove global optimality or lack of headroom for arbitrary direct-M/D trajectories.

### 4.2 Three learning arms

1. `yang_scalar_td3`: a fresh Yang-compatible scalar-reward TD3 engineering baseline, not an exact reproduction of Yang et al.'s SAC implementation.
2. `cd_matd3_no_message`: mode-aware multi-agent TD3 with independently executed actors; the four neighbour slots are zeroed at execution.
3. `cd_matd3_message`: the matched mode-aware multi-agent TD3 with permitted runtime neighbour measurements.

The two CD-MATD3 arms differ only in the runtime neighbour slots presented to the actor. All arms use a training-only joint critic. Therefore:

- message versus no-message is the closest matched comparison;
- message CD-MATD3 versus scalar TD3 is a bundle comparison and does not isolate one algorithmic cause.

### 4.3 Observation and networks

Each actor receives one seven-slot row:

1. scaled local active power;
2. local frequency deviation;
3. local RoCoF;
4-5. frequency deviations of the two ring neighbours;
6-7. RoCoFs of the two ring neighbours.

Each actor is a two-hidden-layer MLP with 256 units per layer and a two-dimensional tanh output. The training-only twin joint critic receives all $4\times7$ observation entries and all $4\times2$ actions. The critic output dimension is one for scalar TD3 and two for CD-MATD3.

### 4.4 Training budget and shared hyperparameters

- Seeds: 401, 402, 403.
- Nine arm-seed runs: three arms times three seeds.
- Per arm-seed run: 43,200 interaction steps and 1,440 attempted episodes.
- Total: 388,800 interaction steps and 12,960 attempted episodes.
- Steps per episode: 30.
- Adam learning rate: $3\times10^{-4}$.
- Discount: $\gamma=0.99$.
- Target update: $\tau=0.005$.
- Replay capacity: 200,000.
- Batch size: 256.
- Target-policy noise: 0.2, clipped at 0.5.
- Exploration noise: 0.1.
- Actor update delay: two critic updates.
- Deterministic final-checkpoint evaluation; no best-checkpoint selection.
- Reward is not used in the physical pass/fail gate.

The stored flag `convergence_diagnostics_valid=true` means only that the run reached the frozen interaction budget without a nonfinite critic loss or another invalid reason. It is **not** evidence that the optimization converged.

## 5. CD-MATD3 objective

The step costs are

\[
c_d=\frac13\left\|\frac{T_d\Delta f}{0.15}\right\|_2^2
+\frac13\left\|\frac{T_dP_{es}}{0.25}\right\|_2^2,
\]

\[
c_c=\frac14\sum_{i=1}^4\left(\frac{\Delta f_i}{0.15}\right)^2
+\frac14\sum_{i=1}^4\left(\frac{\operatorname{RoCoF}_i}{1.0}\right)^2.
\]

The actor objective uses the learned differential and common critic outputs as

\[
\min_\pi -\left(Q_d+\lambda Q_c\right).
\]

The multiplier starts at 1.0 and is updated after every episode:

\[
\lambda_{k+1}
=\operatorname{clip}\left[
\lambda_k+0.05\left(C_{c,k}-3.0\right),0,10
\right],
\qquad C_{c,k}=\sum_t c_c(t).
\]

There is no explicit action-magnitude, action-RMS, total-variation, or slew-use penalty in the two CD-MATD3 cost channels. The scalar TD3 arm uses the V4 scalar reward with $\phi_f=100$, $\phi_{abs}=50$, and $\phi_h=\phi_d=0.0056$; this is a different reward object.

## 6. Registered physical decision rule

The two lower-is-better headline endpoints are:

1. signed off-diagonal common/differential response energy;
2. localized-disturbance differential-frequency energy.

Every arm-seed-profile block must also satisfy:

- common-frequency integral ratio $\le1.03$ relative to the deterministic reference;
- worst-unit peak ratio $\le1.03$;
- worst-unit RoCoF ratio $\le1.03$;
- action RMS ratio $\le1.10$;
- action total-variation ratio $\le1.10$;
- completion, finite values, decoder identity, bounds, slew, and registered saturation guards.

The canary requires positive seed-median improvement on both physical endpoints and all guards. A reward improvement cannot override a physical guard failure.

## 7. R402 registered results

### 7.1 Classification

- Final registered classification: `CANARY-FAIL`.
- All nine training runs finish the frozen budget.
- All 36 learning arm-seed-profile blocks fail both the common no-harm family and the action-stress family.
- The route stops without algorithm replacement or a five-seed Gate-B expansion.
- Three seeds support only a bounded descriptive result, not population inference.

### 7.2 Record-accounting correction that must be respected

The current R402 narrative report and claim card state “264 evaluation records” and the draft expands this as “240 learning + 24 deterministic.” Direct filesystem and formal-manifest accounting instead gives:

- 40 evaluation JSON files;
- each file contains six registered trajectories;
- message CD-MATD3: 12 files, 72 trajectories;
- no-message CD-MATD3: 12 files, 72 trajectories;
- scalar TD3: 12 files, 72 trajectories;
- deterministic reference: four files, 24 trajectories;
- **216 learning trajectories + 24 deterministic trajectories = 240 total trajectories**;
- `formal_manifest.json#/evaluation_records` is 240.

This is a mechanical count discrepancy. It does not change any endpoint, guard, or classification, but the number 264 must not be used as verified input. Please separately state how this accounting defect affects confidence in the paper's reporting integrity without treating it as an algorithmic failure mechanism.

### 7.3 Aggregate deterministic endpoint values

\[
E_{\rm cross,det}=3.4260449381761277\times10^{-4},
\]

\[
E_{\rm diff,det}=2.2148944818784584\times10^{-3}.
\]

### 7.4 Per-seed learning endpoints

| Arm | Seed | Off-diagonal response energy | Disturbance differential energy |
|---|---:|---:|---:|
| scalar TD3 | 401 | 0.000872777540 | 0.005283716452 |
| scalar TD3 | 402 | 0.001574685117 | 0.006869835345 |
| scalar TD3 | 403 | 0.001409921536 | 0.006457486365 |
| CD-MATD3, no message | 401 | 0.001425946230 | 0.005724366685 |
| CD-MATD3, no message | 402 | 0.001342942655 | 0.006924335662 |
| CD-MATD3, no message | 403 | 0.002802644244 | 0.008683936843 |
| CD-MATD3, message | 401 | 0.001594330876 | 0.007307441627 |
| CD-MATD3, message | 402 | 0.001744437851 | 0.007980829948 |
| CD-MATD3, message | 403 | 0.001928966320 | 0.006581981548 |

### 7.5 Seed-median ratios against the deterministic reference

| Arm | Cross ratio | Differential ratio |
|---|---:|---:|
| scalar TD3 | 4.1153 | 2.9155 |
| CD-MATD3, no message | 4.1621 | 3.1263 |
| CD-MATD3, message | 5.0917 | 3.2992 |

Using the convention that a positive number means the message-enabled full method improves on the comparator, the message arm's median increments are:

- versus matched no-message CD-MATD3: $-22.3\%$ cross and $-5.5\%$ differential;
- versus scalar TD3: $-23.7\%$ cross and $-13.2\%$ differential.

These comparisons establish no positive runtime-message increment in this bundle. They do not establish that communication is useless in other observation, delay, architecture, or training settings.

### 7.6 Worst guard ratios by run

| Arm | Seed | Common IAE | Worst peak | RoCoF | Action RMS | Action TV |
|---|---:|---:|---:|---:|---:|---:|
| scalar TD3 | 401 | 1.304 | 1.761 | 2.119 | 1.327 | 2.060 |
| scalar TD3 | 402 | 1.375 | 2.094 | 4.906 | 2.627 | 3.524 |
| scalar TD3 | 403 | 1.300 | 1.694 | 1.461 | 3.033 | 7.165 |
| CD-MATD3, no message | 401 | 1.200 | 1.735 | 2.681 | 3.583 | 3.594 |
| CD-MATD3, no message | 402 | 1.233 | 1.612 | 4.288 | 3.659 | 4.805 |
| CD-MATD3, no message | 403 | 1.145 | 2.363 | 7.381 | 5.759 | 5.036 |
| CD-MATD3, message | 401 | 1.361 | 2.214 | 5.495 | 4.545 | 8.354 |
| CD-MATD3, message | 402 | 1.483 | 3.176 | 4.157 | 4.682 | 5.441 |
| CD-MATD3, message | 403 | 1.171 | 1.737 | 4.186 | 4.373 | 8.234 |

Registered ceilings are 1.03 for the first three columns and 1.10 for the last two. The registered physical saturation ratio is zero for every run. Do not confuse that guard with the separate post-hoc count of normalized actor components satisfying $|a|>0.999$.

## 8. Post-hoc failure forensics

The following quantities were recomputed from the sealed evaluation trajectories, final checkpoints, periodic snapshots, and training manifests. They were not preregistered as causal estimands.

### 8.1 Stored common-cost and multiplier data

Each CD-MATD3 manifest stores only the final 20 values of `episode_common_costs` and `lagrange_trace`, not all 1,440 episodes. Across the six runs, those 120 retained final-episode common costs have:

- minimum 0.023645;
- median 2.023668;
- maximum 6.380282;
- common budget 3.0.

Per-run values are:

| Arm | Seed | Final-20 $C_c$ min | median | max | Final-20 $\lambda$ min | max | final |
|---|---:|---:|---:|---:|---:|---:|---:|
| message | 401 | 0.0564 | 2.2869 | 6.2227 | 0 | 0.1869 | 0.1406 |
| message | 402 | 0.0236 | 2.6994 | 6.3803 | 0 | 0.2193 | 0.1269 |
| message | 403 | 0.0566 | 1.7809 | 3.7243 | 0 | 0.0362 | 0.0145 |
| no message | 401 | 0.0353 | 1.8475 | 3.3123 | 0 | 0.0186 | 0.0043 |
| no message | 402 | 0.0495 | 2.2146 | 5.3195 | 0 | 0.1721 | 0.0268 |
| no message | 403 | 0.0267 | 1.6054 | 4.4655 | 0 | 0.0733 | 0.0485 |

The final multipliers are all much smaller than the initial value 1.0, and every final-20 trace touches zero. However, because only the final 20 episodes are retained, it is not valid to claim from the manifests that the multiplier remained near zero for the entire training run.

Periodic checkpoints exist at episodes 240, 480, 720, 960, 1200, and 1440. A current forensic helper sorts filenames lexicographically, which places `episode1200` and `episode1440` before `episode240`; it also labels the final checkpoint with 43,200 interaction steps while snapshot labels are episode counts. Therefore, its serialized snapshot list must be numerically re-sorted before being interpreted as a trajectory. Final values remain readable; the existing serialized order is not chronological evidence.

### 8.2 Evaluation action-pattern diagnostics

The forensic script aggregates 24 evaluation trajectories per arm-seed. For each trajectory there are 30 controller steps, four actors, and two normalized action components, giving 5,760 scalar action-component samples per arm-seed.

| Arm | Seed | Mean $|a|$ | Fraction of component updates at the 0.25 slew limit |
|---|---:|---:|---:|
| deterministic | — | 0.07912 | 0.00417 |
| scalar TD3 | 401 | 0.10181 | 0.00191 |
| scalar TD3 | 402 | 0.17967 | 0.03108 |
| scalar TD3 | 403 | 0.19508 | 0.14722 |
| CD-MATD3, no message | 401 | 0.29036 | 0.06354 |
| CD-MATD3, no message | 402 | 0.31503 | 0.10156 |
| CD-MATD3, no message | 403 | 0.48652 | 0.15208 |
| CD-MATD3, message | 401 | 0.37032 | 0.19115 |
| CD-MATD3, message | 402 | 0.36922 | 0.12500 |
| CD-MATD3, message | 403 | 0.37517 | 0.16302 |

The CD arms have larger actions and more slew-limit use than the deterministic reference. Because the CD objective has no explicit action-effort term, this pattern is consistent with reward/action-stress misalignment. It is not by itself proof that the missing penalty caused either physical endpoint failure.

### 8.3 Post-hoc frequency-cost reconstruction

The forensic helper reconstructs common cost from physical frequency and RoCoF. For differential cost, however, it explicitly sets

```python
power = np.zeros((freq.shape[0], 4))
```

because the evaluation JSON files do not store $P_{es}$. Consequently, the reported post-hoc differential totals contain only the $T_d\Delta f$ term and omit the $T_dP_{es}$ term that was present during training. They must be called **frequency-only differential-cost reconstructions**, not the full CD training objective.

| Arm | Seed | Total common cost | Frequency-only differential total |
|---|---:|---:|---:|
| deterministic | — | 29.5830 | 0.9463 |
| scalar TD3 | 401 | 50.6414 | 2.6066 |
| scalar TD3 | 402 | 57.0102 | 4.0990 |
| scalar TD3 | 403 | 50.1612 | 3.4601 |
| CD-MATD3, no message | 401 | 39.3268 | 2.9558 |
| CD-MATD3, no message | 402 | 48.7599 | 4.5942 |
| CD-MATD3, no message | 403 | 42.1967 | 5.5827 |
| CD-MATD3, message | 401 | 52.4801 | 4.4146 |
| CD-MATD3, message | 402 | 65.1755 | 5.9776 |
| CD-MATD3, message | 403 | 42.4072 | 4.0915 |

This reconstruction shows that the frequency component remains worse than the deterministic reference. It cannot establish how well the learned policies optimized the complete training $c_d$ because the power term is unavailable.

### 8.4 Message/no-message action correlations

The flattened deterministic-evaluation action correlations between the matched message and no-message arms are:

| Seed | Pearson correlation |
|---:|---:|
| 401 | -0.1404 |
| 402 | 0.0373 |
| 403 | 0.1542 |

These values show that the policies differ substantially. They do not identify whether the neighbour channels were redundant, noisy, poorly represented, insufficiently explored, or simply learned differently.

### 8.5 Missing diagnostics

The following are unavailable or incomplete:

- full 1,440-episode return and cost histories;
- full chronological multiplier history;
- saved per-update actor losses;
- saved per-update critic losses beyond the run-time finite/nonfinite check;
- Bellman residuals or held-out critic calibration;
- gradient norms, parameter-update norms, or target-network drift;
- replay-buffer state distribution and coverage diagnostics;
- complete $P_{es}$ trajectories in the evaluation JSON files;
- conditional-information or intervention test for the runtime message slots;
- actual reduced DAE input Jacobians for direct M/D and energy-port actions.

Therefore “optimization did not converge” is a plausible hypothesis, not an observed fact.

## 9. Separate constructive evidence: energy-port object

This is a distinct non-learning experiment and must not be pooled numerically with R402.

- Direct M/D commands are pinned to zero.
- A 0.4-Hz ring-edge bandpass acts through state-dependent feasible active-power headroom.
- Structure:

\[
F(s)=K\frac{2\zeta\omega_m s}
{s^2+2\zeta\omega_m s+\omega_m^2},
\qquad \omega_m=2\pi(0.4),\quad\zeta=0.35.
\]

- Normalized ring-edge command is zero-sum to numerical precision and clipped at $\pm0.70$ before the feasibility-native mapping.
- R408 development result at frozen $K=3.5$:

\[
r_d=0.938947,\qquad r_{\rm cross}=0.539791,
\]

with all guards passing.
- R409 one-use unseen-bank result for the same frozen controller:

\[
r_d=0.9382180714,\qquad
r_{\rm cross}=0.7937304482,
\]

with all guards passing.
- One topology, one development bank, one held-out bank, one frozen candidate; no MARL or topology-generalization claim.

This evidence proves that the registered joint target is not empty for the energy-port object. Because its actuator, estimator, window, bank, and reference differ from R402, it does not by itself prove that the action basis caused the R402 learning failure.

## 10. Mathematical results already audited

### 10.1 Exact separation in an ideal reduced model

For

\[
\dot\theta=\omega,\qquad
M\dot\omega=-\omega_nL\theta-D\omega+w,
\]

with positive diagonal $M,D$, a balanced symmetric coupling $L$, full common/differential input and output directions, and

\[
G_{\omega w}(s)=s(s^2M+sD+\omega_nL)^{-1},
\]

all-frequency exact common/differential separation implies $M=mI$ and $D=dI$. This is an ideal reduced-model structural theorem. It is not a finite-window, nonlinear-DAE, actuator-feasibility, or MARL impossibility theorem.

### 10.2 Local multiplicative-parameter lemma

For the smooth zero-state model

\[
\dot x=A(\kappa(x))x+B_ww,
\]

the state Jacobian at $x=0$ is $A(\kappa(0))$; the policy slope is multiplied by $x$ and does not enter the first-order state Jacobian. This establishes limited local first-order authority for that multiplicative model, not finite-amplitude impossibility.

For an index-1 DAE

\[
\dot x=f(x,y,u,w),\qquad 0=g(x,y,u,w),
\]

valid algebraic elimination gives

\[
A_r=f_x-f_yg_y^{-1}g_x,
\qquad
B_{u,r}=f_u-f_yg_y^{-1}g_u.
\]

State feedback has local Jacobian

\[
A_r+B_{u,r}D\kappa(0).
\]

Thus action dependence in the algebraic equations can restore an additive first-order channel. The actual project-specific $f_x,f_y,f_u,g_x,g_y,g_u$ matrices and conditioning have not been established for the compared action objects.

## 11. Candidate failure mechanisms to audit

Please include at least the following competing explanations. Do not select one in advance.

1. **Multiplier/budget calibration:** the common budget of 3.0 and step 0.05 drove $\lambda$ close to zero for much of the retained tail.
2. **Missing action-effort regularization:** the CD objectives did not penalize magnitude, slew use, RMS, or total variation.
3. **Objective/endpoint mismatch:** training costs are not identical to the registered signed off-diagonal and finite-window disturbance endpoints.
4. **Optimization insufficiency:** 43,200 steps, function approximation, critic error, or exploration noise may have been insufficient.
5. **Partial observability/information insufficiency:** the seven-slot memoryless rows may not identify the state needed for the target response.
6. **Message-value failure:** neighbour slots may be redundant, noisy, poorly normalized, or difficult for the actor to exploit.
7. **Credit assignment and centralized-critic mismatch:** four independent actors share a joint critic and two global cost channels.
8. **Action-decoder geometry:** asymmetric piecewise decoding, slew projection, and physical clamps alter gradients and reachable trajectories.
9. **Direct-M/D physical authority:** parameter modulation may offer limited local incremental authority even though the deterministic controller proves nonzero finite-amplitude authority.
10. **Strong-comparator headroom:** the deterministic law may already occupy a strong region of the tested direct-M/D controller family.
11. **Distribution shift:** training uses four development profiles and evaluation uses four different profiles.
12. **Action-basis alignment:** the successful energy-port bandpass may align more directly with differential dynamics, but the experiments do not isolate this cause on one matched object.
13. **Implementation or accounting defects:** count/provenance discrepancies may affect reporting confidence without causing the policy failure.

## 12. Required GPT Pro analysis

### Task A: evidence and arithmetic audit

1. Recompute the record count from the stated design and identify 240 versus 264 as correct or incorrect.
2. Check every percentage, ratio, and qualitative statement for consistency.
3. Identify whether any numerical fact is being used outside its actual unit of analysis.
4. Separate registered guard quantities from post-hoc diagnostic definitions.
5. Explain the scientific impact of the missing `formal_execution.json`, the internal `formal_analysis.json#/round` value `R401`, and the R402 formal manifest/report count disagreement. Treat these as provenance/reporting issues unless a causal link to the policy outcome is demonstrated.

### Task B: multiplier dynamics

Analyze

\[
\lambda_{k+1}=\Pi_{[0,10]}
\left(\lambda_k+0.05(C_{c,k}-3)\right).
\]

1. State exactly what can be inferred from the final-20 cost and multiplier samples.
2. Determine whether the phrase “the common constraint was deleted” is mathematically justified, too strong, or false.
3. Distinguish a small multiplier from a small contribution $\lambda Q_c$; the scale of $Q_c$ may matter.
4. State what additional stored quantities are needed to bound the fraction of actor updates for which the common term was negligible.
5. If possible, derive a sufficient condition involving $\lambda$, $\|\nabla_a Q_c\|$, and $\|\nabla_a Q_d\|$ under which the common contribution is negligible in the actor gradient. Clearly label unavailable terms.

### Task C: causal identifiability and competing explanations

Construct a causal DAG containing at least:

- profile/scenario;
- observation/information pattern;
- runtime messages;
- actor/critic approximation;
- replay coverage;
- exploration noise;
- reward/cost definition;
- common budget and multiplier;
- action magnitude and slew projection;
- direct-M/D physical channel;
- optimization/convergence state;
- common-mode endpoints;
- differential endpoints;
- registered guard failures.

For every proposed causal arrow, classify it as:

1. identified by a controlled intervention;
2. mechanically implied by code/equations;
3. supported only by association;
4. plausible but not identified;
5. contradicted by existing evidence.

Use inference-to-the-best-explanation criteria: explanatory scope, parsimony, fit to all observations, and predictive consequences. Preserve at least the two strongest alternative explanations.

### Task D: action-effort interpretation

1. Determine which outcomes the absence of an action-effort term can directly explain.
2. Decide whether it can explain only action RMS/TV failure or also endpoint degradation.
3. Explain why the scalar arm, which uses a different reward with action-related terms, still failing is important counter-evidence against a single-cause story.
4. Give manuscript-safe wording that does not infer causality from action magnitude alone.

### Task E: optimization and convergence

1. Determine whether any available diagnostic establishes convergence or nonconvergence.
2. Explain why “reached 43,200 steps with finite critic losses” is not a convergence certificate.
3. List the minimum logs needed to diagnose critic divergence, overestimation, actor collapse, insufficient coverage, or premature budget termination.
4. State whether more random seeds, without better diagnostics or a changed prospective contract, would identify an optimization cause.

### Task F: runtime-message value

1. Distinguish the estimand “message arm minus no-message arm in this bundle” from the causal claim “messages are useless.”
2. Explain what the near-zero cross-policy action correlations do and do not establish.
3. Propose a mathematically defensible value-of-information or conditional-information test for the neighbour slots.
4. State whether such a test can be performed from the current stored data; if not, list the exact missing variables or interventions.

### Task G: direct-M/D versus energy-port authority

1. Reconcile the strong deterministic direct-M/D improvement with the local multiplicative-authority lemma.
2. Explain why the deterministic result rules out “direct M/D has no authority” but not “direct M/D has limited learnable incremental headroom.”
3. Determine whether the separate energy-port success permits the claim that action-basis mismatch caused R402.
4. Formulate the smallest valid DAE comparison using $A_r$, $B_{u,r}$, finite-horizon response maps, controllability/authority Gramians, common/differential projections, and conditioning.
5. Specify which actual Jacobians and operating points must be supplied before this comparison is evidence rather than theory.

### Task H: minimal additional evidence

For each unresolved mechanism, give the minimum one of:

- no new work required; existing evidence is sufficient;
- read-only reanalysis of existing artifacts;
- additional logging only;
- a new prospective but non-training calculation;
- a new prospective controlled experiment;
- a complete successor MARL study with fresh seeds and fresh banks.

Rank each by:

1. necessity for the current ICEMS conference paper;
2. causal identification value;
3. computational cost;
4. risk of creating an incomparable new object;
5. suitability as future journal work.

Do not recommend an algorithm sweep. Do not recommend more seeds as a substitute for mechanism identification.

### Task I: manuscript consequences

Provide submission-quality English for:

1. one Results sentence reporting the bounded R402 failure;
2. one Discussion paragraph separating established design facts from unisolated mechanisms;
3. one Limitations paragraph covering missing convergence logs and causal non-identifiability;
4. one sentence comparing R402 with the separate energy-port evidence without pooling them;
5. one replacement for any statement equivalent to “action/interface mismatch dominates optimization failure” if that wording is too strong;
6. a list of forbidden stronger statements.

The title must remain unchanged, but the prose must make clear that the paper investigates the MARL objective rather than claiming successful MARL decoupling.

## 13. Required output format

Return exactly these sections:

1. **Executive verdict** — no more than 250 words.
2. **Data and provenance corrections** — table with issue, correct value, consequence, required repair.
3. **Causal DAG** — Mermaid or a clearly specified directed-edge list.
4. **Failure-mechanism classification** — table with mechanism, evidence, epistemic status, alternative explanation, manuscript-safe claim.
5. **Multiplier analysis** — equations, assumptions, and unavailable quantities.
6. **Optimization/convergence analysis**.
7. **Runtime-message identifiability analysis**.
8. **Direct-M/D versus energy-port mechanism boundary**.
9. **Minimum additional evidence matrix** — current conference necessity versus future-work value.
10. **Manuscript-ready English text**.
11. **Forbidden claims**.
12. **Unresolved inputs required for a stronger conclusion**.

Every conclusion must be labeled as one of:

- `PROVED-MATHEMATICALLY`;
- `REGISTERED-EMPIRICAL`;
- `POST-HOC-DIAGNOSTIC`;
- `PLAUSIBLE-NOT-IDENTIFIED`;
- `CONTRADICTED`;
- `UNAVAILABLE`.

## 14. Statements that must not be accepted without new evidence

- MARL cannot decouple paralleled VSGs.
- Direct M/D control has no physical authority.
- All finite-order LTI or all causal controllers are infeasible.
- The energy-port result proves that the direct-M/D action basis caused R402.
- The common constraint was absent throughout all 1,440 episodes.
- The CD-MATD3 policies failed to converge.
- Runtime messages are intrinsically useless or harmful.
- More training would necessarily fix or necessarily fail to fix the result.
- The action-effort omission is the sole cause of the endpoint failure.
- The actual ANDES DAE has $B_{u,r}=0$ for direct M/D.
- One fixed topology and one held-out bank establish topology generalization.
- The post-hoc frequency-only cost reconstruction equals the complete training differential objective.

## 15. Source files and hashes

The following local files are the provenance package. If only this Markdown document is supplied to GPT Pro, treat the hashes as provenance metadata rather than independently verified content.

| Source | SHA-256 | Role |
|---|---|---|
| `paper/yang_md_decoupling_marl/reports/R399.md` | `b9e1a8e182362b0f6326e6ab208df2a13767d1903222ce4b8e4988fee401a2b7` | deterministic headroom feed |
| `paper/yang_md_decoupling_marl/reports/R402.md` | `3bbe8dac082abfaecac0ae114f9e2f5a10893937b97e110df5f19631b688cd6b` | registered canary feed; contains the count wording conflict |
| `results/research_loop/r402_cd_matd3_canary/formal_analysis.json` | `1b65ff7789483d1f1c6e36fce86d1da88e02f54009aa82ef6657711a44d705b4` | classifier and guard failures |
| `results/research_loop/r402_cd_matd3_canary/endpoint_table.json` | `752f0939c9593bce4eae922c7eb320f21dfaf513700202cd830bf26485e6d2e3` | endpoint and guard ratios |
| `results/research_loop/r402_cd_matd3_canary/formal_manifest.json` | `8c5c3ce76562d9d9d9976366b64aa3bbc688fdcbeac8d0380c4abf13b1c65764` | file list, hashes, nine runs, 240-record count |
| `paper/yang_md_decoupling_marl/working/canary_failure_forensics_r402.md` | `9b494d54b6bf5dee6d18552ce7a69222955e2fff6adf2756049434ddd511bd8b` | non-authoritative prior forensic interpretation |
| `probes/canary_failure_forensics.py` | `8387252f556a361c71a2ef4aa7fc3e903f9607b8acddb0302c86b542592f9db1` | read-only forensic computation; contains the power-zero and snapshot-order limitations |
| `src/andes_rl_kundur/evaluation/cd_matd3_canary.py` | `811ffd314a450e3c700270158437e7326d0d1bbdebc26fdb81f2783a53129f78` | frozen contract and classifier |
| `scripts/run_r402_cd_matd3_canary.py` | `c1b15ce86bda9bb551daf67dda9d2ee5fb798244752dedd2a9d6e6d0fc3caeed` | training/evaluation implementation and retained-log semantics |
| `paper/yang_md_decoupling_marl/reports/R408.md` | `beb26b9a2f23a875879ecdd5aa2a5337a2c17cfcbc58dbc353c7cfec1c9e0108` | energy-port development evidence |
| `paper/yang_md_decoupling_marl/reports/R409.md` | `9fe768f21cbc76ad8e7ca00cd4df3ded0caebd270d16cc9b1cc9dcb0dc4793f1` | frozen energy-port unseen-bank evidence |
| `paper/yang_md_decoupling_marl/working/theory_audit_bundle/IMPORT_NOTE.md` | `7a6ac8dfef87c61fc12397515858270a6b8d6a7b495b374e38faf77157e47ed9` | mathematical validity boundaries |

## 16. Final instruction

The goal is not to rescue a preferred narrative. The goal is to determine the strongest scientifically defensible explanation of the observed canary failure while preserving all serious alternatives. If the current data cannot identify a cause, say so explicitly and design the smallest discriminating evidence request. Theory may bound an interpretation, but it must not be presented as new plant evidence.
