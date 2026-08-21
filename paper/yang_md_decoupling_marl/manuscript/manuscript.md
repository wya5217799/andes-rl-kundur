# Decoupling-Oriented Coordination of Paralleled  VSGs With Multi-Agent Reinforcement Learning

> Draft status: evidence-bounded working Markdown source for ICEMS 2026. The title states the investigated objective; it does not presume that the tested MARL controllers achieve it. Conversion to the official A4 IEEE template must condense this source to 4–6 pages, omit page numbers, and restore the authors' metadata.

## Abstract

Parallel virtual synchronous generators (VSGs) are network coupled: a disturbance or control action intended for one aggregate mode can excite other common or differential frequency coordinates. Multi-agent reinforcement learning (MARL) is therefore an appealing coordination mechanism, but reward improvement alone does not establish physical decoupling, and an unsuccessful learner does not establish that decoupling is impossible. This paper evaluates that distinction on a fixed-connectivity, modified Kundur two-area system in ANDES. The main comparison gives four independently executed agents bounded direct authority over their own virtual inertia and damping. Decoupling is evaluated from signed common/differential probe responses and disturbance-driven differential energy, subject to common-mode and action-stress no-harm guards. A strong deterministic local-neighbour controller reduces development-set off-diagonal response energy by 60.79% and differential disturbance energy by 64.13% relative to zero action. An outcome-seeing oracle over the same finite nine-law family finds no further improvement on four evaluation profiles. Three fixed-budget learning arms—scalar TD3, a nominal no-message mode-aware multi-agent TD3 arm, and a message-enabled counterpart—are evaluated over three seeds. Their median off-diagonal energies are 3.90, 2.95, and 5.26 times the deterministic reference, respectively, and all learning blocks violate the registered common-mode and action-stress guards. An initial execution masked the nominal no-message arm's neighbour slots only at interaction and evaluation; after repairing the information contract so that the mask applies inside every actor path, a re-execution still fails the guards and shows a negative three-seed-median message increment of 78.43% off-diagonal and 26.74% disturbance differential energy relative to the repaired no-message arm, so runtime neighbour messages add no positive coordination increment for this bundle. A post-hoc source audit also identifies an unresolved mismatch between stateful slew-limited execution and unslewed actor/target optimization. A reduced-model analysis shows why exact common/differential separation is structurally restrictive and why zero-bias dynamic inertia/damping feedback has limited local first-order authority. However, a separate energy-port experiment produces a low-order ring-edge bandpass controller inside the prescribed joint target region on both development and previously unseen data. The combined evidence supports a bounded conclusion: the tested direct inertia/damping MARL bundle fails the registered physical canary, whereas the separate structured object shows that the joint target is nonempty. A registered slew-state repair then flips the endpoints—the message arm reaches 0.70 and 0.71 of the deterministic reference with a positive message increment—without flipping the guard verdict, localizing the residual failure to the objective-to-decision-contract gap. The evidence does not establish that MARL, causal coordination, or decoupling is impossible in general.

**Keywords—** virtual synchronous generator, multi-agent reinforcement learning, frequency coordination, common and differential modes, negative results, energy-port control.

## 1. Introduction

Grid-forming and VSG controls are increasingly used to make power-electronic resources contribute frequency-forming behaviour. Their virtual inertia and damping parameters can be adapted to operating conditions [1]–[3], while distributed secondary and consensus controls provide established ways to coordinate inverter-based resources [4], [5]. These developments motivate learning-based coordination: a local policy can condition an individual converter's parameters on its own measurements and selected neighbour information, potentially avoiding an explicit global model. Deep reinforcement learning has consequently been applied to VSG parameter adaptation and frequency support [6]–[8].

The coordination claim is nevertheless easy to overstate. Parallel VSGs share an electrical network, so local changes to virtual inertia or damping modify a coupled closed loop. A policy may improve a scalar reward while worsening the physical transfer from a common excitation to differential frequency, or the reverse. It may also obtain an apparent differential benefit by degrading common-frequency quality, increasing rate of change of frequency (RoCoF), or repeatedly hitting action and slew limits. Moreover, providing neighbour observations does not by itself demonstrate that communication creates an identifiable coordination benefit: the message-enabled controller must outperform a capacity- and budget-matched controller without those runtime messages.

These issues are especially important for negative results. MARL studies are sensitive to environment definitions, training budgets, seed variation, and evaluation protocol [9], [10]. A failed learning run cannot prove that no useful policy exists. Conversely, an outcome-seeing oracle over a finite hand-designed family is only an upper bound for that family; it is not an oracle over all causal controllers. Stronger physical and mathematical boundaries are therefore needed before interpreting a learning failure.

This paper investigates, rather than assumes, whether MARL can provide decoupling-oriented coordination for four parallel VSG proxies. The main experimental object follows a direct virtual-inertia/virtual-damping interface: each actor writes only its own bounded two-dimensional action, and all reported outcomes come from physical 60-Hz endpoints of a phasor-domain differential-algebraic-equation (DAE) simulation. The study separates common and differential coordinates, uses signed probes to estimate off-diagonal response energy, measures disturbance-driven differential energy, and enforces common-mode and action-stress guards. A strong deterministic controller is established before any learning comparison. The learning study fixes the action interface, training budget, actor/critic capacity, seeds, and checkpoint rule across scalar, nominal no-message, and message-enabled arms; a post-hoc audit separately tests whether the intended information contrast was preserved in implementation.

The resulting evidence is mainly negative for the tested MARL route, but not for the decoupling objective itself. A separate, explicitly non-pooled experiment replaces direct inertia/damping modulation with feasibility-native energy-port actuation and evaluates a structured ring-edge bandpass controller. The frozen controller enters the prescribed joint target region on a disclosed development bank and passes a one-use unseen bank without tuning. This constructive result prevents the manuscript from turning a learning failure into a false impossibility theorem. It motivates an action-basis and controller-structure hypothesis, but the unmatched objects do not identify that hypothesis as the cause of the MARL result.

The contributions are:

1. A guard-first evaluation protocol for decoupling-oriented VSG coordination, based on physical common/differential endpoints rather than reward alone, together with an information-contract audit that prevents an invalid message comparison from being promoted into a coordination claim.
2. A conditional reduced-model theorem showing that exact common/differential transfer separation requires homogeneous effective inertia and damping in an ideal balanced network, together with a first-order authority lemma for zero-bias multiplicative parameter feedback.
3. A bounded three-seed comparison showing that the tested MARL arms do not improve a strong deterministic direct-inertia/damping controller, plus a source-level diagnosis showing why the nominal message/no-message contrast cannot identify runtime-message value.
4. A constructive auxiliary result showing that a frozen low-order energy-port controller enters the joint decoupling region on development data and transfers to an unseen bank, thereby localizing the negative conclusion to the tested learning interface, bundle, topology, simulator, and finite evaluation banks.

The paper is an evaluation study with a constructive control companion. It is not a strict reproduction of any single published MARL algorithm, a universal comparison between learning and classical control, or a proof that causal decoupling is impossible.

## 2. Related Work

Adaptive VSG studies have shown that scheduled virtual inertia and damping can improve frequency response and power oscillation behaviour [1]–[3]. Other work modifies virtual impedance or converter-side control to manage coupling and power sharing [12]. These methods demonstrate that the actuation structure is a design variable rather than a neutral implementation detail.

Distributed averaging proportional-integral and related consensus controls provide model-based coordination with explicit information structures [4], [5]. Their guarantees do not automatically transfer to the arithmetic common/differential coordinates used in this paper, but they provide a strong reason to compare learning against structured local-neighbour controllers rather than against zero action alone. Stability analyses of droop-controlled microgrids similarly emphasize network and controller assumptions when making modal claims [11].

Learning-based VSG controllers have been proposed for coordinated parameter adaptation and frequency support [1], [6]–[8]. Yang et al. use multi-agent soft actor-critic for parallel VSG parameter cooperation [1]. The scalar TD3 arm in this paper shares the four-actor direct-inertia/damping scientific object and permitted measurements, but it is an engineering baseline rather than an exact reproduction of that algorithm. This distinction is essential: the present results test a registered bundle, not the full class of SAC, TD3, or MARL methods.

MARL evaluation research recommends controlling seeds, budgets, environment access, and ablations, and warns against conclusions based only on aggregate training reward [9]. Real-world reinforcement-learning studies also identify constraints, partial observability, distribution shift, and safe exploration as central deployment barriers [10]. The present work adopts that evaluation perspective in a power-system setting: physical trajectories and frozen guards determine the verdict, while reward is excluded from the final gate.

## 3. Problem Formulation and Structural Analysis

### 3.1 Two experimental objects

The paper distinguishes two control objects.

**Object A: direct inertia/damping modulation.** Four VSG proxies are treated as four actors. Actor $i$ produces

\[
a_i=[a_i^M,a_i^D]^\top\in[-1,1]^2,
\]

with a componentwise slew limit of 0.25 per 0.2-s update. The asymmetric physical decoder is

\[
\Delta q(a)=
\begin{cases}
600a, & a\ge 0,\\
200a, & a<0,
\end{cases}
\qquad q\in\{M,D\},
\]

followed by the physical lower bounds $M_i\ge20$ and $D_i\ge10$. Each actor writes only its own row. No actor directly injects active power.

**Object B: feasibility-native energy-port actuation.** A separate auxiliary experiment applies a ring-edge, zero-sum normalized command through state-dependent feasible power headroom. The legacy direct-M/D path is pinned to zero. Because this action basis has different physical authority and constraints, Object B is not pooled statistically with Object A and is not used to claim that the tested MARL controller succeeded.

This separation prevents a category error: evidence that a power-like energy port admits a useful structured controller is evidence about decoupling feasibility, but not evidence that a direct-M/D MARL policy learned that controller.

### 3.2 Common and differential endpoints

Let $\Delta f\in\mathbb R^4$ collect the physical frequency deviations of the four VSG proxies. The arithmetic common coordinate is

\[
z_c=\frac14\mathbf 1^\top\Delta f,
\]

and the registered differential coordinates are

\[
z_d=T_d\Delta f,\qquad
T_d=
\begin{bmatrix}
1/2&1/2&-1/2&-1/2\\
1/\sqrt2&-1/\sqrt2&0&0\\
0&0&1/\sqrt2&-1/\sqrt2
\end{bmatrix}.
\]

For a signed probe pair with amplitude $\varepsilon$, the normalized odd response is

\[
y_{\rm odd}(t;\varepsilon)=
\frac{y(t;+\varepsilon)-y(t;-\varepsilon)}{2\varepsilon}.
\]

Off-diagonal response energy aggregates common-input-to-differential-output and differential-input-to-common-output terms over the frozen finite window. A second endpoint aggregates differential-frequency energy under localized disturbances. Both are lower-is-better. The experiment additionally constrains common-frequency integral, worst-unit peak, RoCoF, action RMS, action total variation, saturation, slew, convergence, and run completion. Thus “decoupling-oriented” means reducing the registered off-diagonal and disturbance endpoints without buying the reduction through common-mode or actuator harm. It does not mean exact modal diagonalization of the full nonlinear DAE.

### 3.3 Exact separation in an ideal reduced model

Consider the idealized electromechanical model

\[
\dot\theta=\omega,\qquad
M\dot\omega=-\omega_n L\theta-D\omega+w,
\tag{1}
\]

where $L=L^\top\succeq0$, $L\mathbf1=0$, the network is connected, and $M,D\succ0$ are diagonal. Let $P_c=\mathbf1\mathbf1^\top/4$ and $P_d=I-P_c$.

**Proposition 1 (conditional exact-separation criterion).** In (1), the transfer from $w$ to $\omega$ has zero common-to-differential and differential-to-common blocks for every complex frequency where it is defined,

\[
P_dG_{\omega w}(s)P_c=0,
\qquad
P_cG_{\omega w}(s)P_d=0,
\tag{2}
\]

if and only if $M=mI$ and $D=dI$ for positive scalars $m,d$. Under the same assumptions, either one of the two complete cross-block identities alone is sufficient.

**Proof.** The transfer matrix is

\[
G_{\omega w}(s)=s(s^2M+sD+\omega_nL)^{-1}.
\]

Its high-frequency expansion begins with

\[
G_{\omega w}(s)=s^{-1}M^{-1}
-s^{-2}M^{-1}DM^{-1}+O(s^{-3}).
\]

Assume first that $P_dG_{\omega w}P_c\equiv0$. The first coefficient gives $P_dM^{-1}\mathbf1=0$. Because $M$ is diagonal, $M^{-1}\mathbf1$ can be proportional to $\mathbf1$ only when $M=mI$. With this substitution, the second coefficient gives $P_dD\mathbf1=0$ and hence $D=dI$. The opposite complete cross identity yields the same conclusion through the corresponding row conditions. Conversely, if $M=mI$ and $D=dI$, then $M$, $D$, and the balanced symmetric $L$ all preserve the common and differential subspaces, so every resolvent and hence $G_{\omega w}$ is block diagonal in those subspaces. This proves the claim.

Proposition 1 is deliberately narrow. It concerns exact all-frequency separation in a balanced, symmetric, reduced linear model with full common/differential input directions. Connectivity and positive semidefiniteness support the physical Laplacian interpretation but are not needed for the algebraic equivalence itself. The result is not a theorem about approximate finite-window decoupling, the full ANDES DAE, asymmetric or unbalanced networks, rank-deficient measured outputs, saturated action maps, or learned nonlinear policies. A recovered numerical coupling matrix with nonzero symmetry or balance residual cannot be inserted into this proposition as though it were an exact Laplacian.

### 3.4 Local authority of dynamic inertia/damping feedback

The direct-M/D input is multiplicative: it changes coefficients that multiply the state rather than adding a power input. This creates a second, more local limitation.

**Lemma 1 (first-order parameter-feedback invariance).** Let a smooth closed loop near $x=0$ be

\[
\dot x=A(u)x+B_ww,\qquad u=\kappa(x),\qquad u_0=\kappa(0).
\tag{3}
\]

Then the state Jacobian at the equilibrium is $A(u_0)$; it does not contain $D\kappa(0)$. In the swing-form specialization, the Jacobian is

\[
A_{\rm cl}(u_0)=
\begin{bmatrix}
0&I\\
-M(u_0)^{-1}\omega_nL&-M(u_0)^{-1}D(u_0)
\end{bmatrix}.
\tag{4}
\]

**Proof.** Differentiating $A(\kappa(x))x$ with respect to $x$ yields $A(u_0)$ plus terms proportional to $x$; the latter vanish at $x=0$. This proves the claim.

For a semi-explicit index-1 DAE, $\dot x=f(x,y,u,w)$ and $0=g(x,y,u,w)$, the same conclusion does not follow automatically. If $g_y$ is nonsingular at the equilibrium, local algebraic elimination gives

\[
A_r=f_x-f_yg_y^{-1}g_x,
\qquad
B_{u,r}=f_u-f_yg_y^{-1}g_u,
\]

and state feedback has local Jacobian $A_r+B_{u,r}D\kappa(0)$. Action dependence in the algebraic equations can therefore create an additive first-order channel even when $f_u=0$. Lemma 1 transfers to the reduced DAE only if $B_{u,r}D\kappa(0)=0$. The required project-specific DAE Jacobians have not been identified here, so this extension is a boundary on the lemma rather than an explanation established for the measured trajectories.

Thus, within the stated zero-state multiplicative model, a zero-bias memoryless state-feedback M/D law cannot change the baseline local Jacobian through its policy slope; its first-order influence arises through its equilibrium parameter value $u_0$. This is not an impossibility result for finite disturbances. The implemented deterministic law and decoder are piecewise and include absolute-value operations, so a smooth odd-response expansion and a universal “first difference occurs at cubic order” statement would be unjustified. Under the additional assumptions of locally Lipschitz same-bias controllers, a shared first-order plant map, and one fixed active-mode sequence, their state difference on a fixed horizon is bounded by $O(\varepsilon^2)$; asymmetric one-sided branches mean that the signed-pair difference may also be $O(\varepsilon^2)$ rather than cubic. A geometric-amplitude scaling test of the implemented law (amplitudes $\varepsilon_0 2^{-k}$, $k=0,\ldots,5$, on the evaluation profiles) measures the law-versus-zero-action controller-to-controller signed-pair odd response as quadratic-leading, with log-log slopes in $[1.68, 1.85]$ ($R^2 \ge 0.997852$ across all 12 profile–pair blocks) rising toward $2.0$ at the small-amplitude end, consistent with asymmetric one-sided branch coefficients; a cubic leading term is not supported on this amplitude range. The lemma does not cover additive actuation, dynamic policies with augmented controller states, or sampled-data effects; it only identifies a local structural disadvantage of the stated multiplicative model relative to an additive power input.

### 3.5 Why no general tradeoff theorem is claimed

The registered cross and differential metrics use different input families, output combinations, finite windows, normalization rules, and nonlinear execution maps. A Bode or Poisson integral for one sensitivity function therefore cannot be applied directly to prove a product lower bound between them. Indeed, an earlier measured structured-controller point gives $r_d r_{\rm cross}=1.0346\times0.6778=0.7013$, below the target product $0.95\times1.10=1.045$. Nor can failure along one or two one-dimensional gain sweeps establish infeasibility of all finite-order linear controllers. A controller-class certificate would require a valid Youla or system-level parameterization, internal-stability conditions, robust finite-window response constraints, and a verified primal/dual infeasibility result.

## 4. Experimental Methodology

### 4.1 Simulator and scenario partitions

All physical trajectories use ANDES 2.0.0 on a fixed-connectivity modified Kundur two-area model at 60 Hz. The main non-learning direct-M/D screen uses two heterogeneous development profiles and four unseen evaluation profiles. Each profile includes signed common, differential, and localized disturbance pairs. Controller updates occur every 0.2 s over a 6-s post-disturbance window.

The learning canary uses a fresh partition of four development and four evaluation profiles. Each of the nine arm–seed runs uses 43,200 interaction steps and 1,440 attempted episodes, for 388,800 steps and 12,960 attempted episodes in total. Training reward is not used to classify the final physical gate.

The energy-port auxiliary study first uses a disclosed development protocol, 0.2-s updates for 50 steps, and 30 physical records per arm. Seventeen predeclared arms produce 510 valid records and 25,500 total time steps. The selected $K=3.5$ controller is then frozen and evaluated once on a previously unused bank comprising one signed-probe condition and two disturbance conditions. Zero action, the local auxiliary reference, and the candidate each produce ten records, for 30 held-out records in total. These auxiliary data do not share an action basis with the learning comparison.

### 4.2 Deterministic controller and finite oracle

The main comparator bank contains zero action and nine deterministic local-neighbour dynamic M/D laws. A single law is selected using development profiles. For diagnostic headroom, a nondeployable outcome-seeing oracle may select one of the same nine laws separately for each evaluation profile after observing its outcomes. If the oracle cannot improve on the development-selected law, the conclusion is only that this finite controller bank contains no additional profile-conditional headroom on the tested evaluation bank. A registered follow-up extends the bank to 21 laws (a densified gain grid plus one PI-type law) so that the same oracle statement covers that larger family.

The nine laws use inertia and damping gains from $\{0.5,1,2\}^2$. For unit $i$ with ring neighbours $\mathcal N_i$, the selected gain pair is $(k_M,k_D)=(2,2)$ and its unprojected targets are

\[
a_i^M=\tanh\!\left[k_M\left(
|\Delta f_i|+|\dot f_i|
-\frac{1}{|\mathcal N_i|}\sum_{j\in\mathcal N_i}
(|\Delta f_j|+|\dot f_j|)\right)\right],
\]

\[
a_i^D=\tanh\!\left[k_D\left(
|\Delta f_i|
+\frac{1}{|\mathcal N_i|}\sum_{j\in\mathcal N_i}|\Delta f_i-\Delta f_j|
+\frac{1}{|\mathcal N_i|}\sum_{j\in\mathcal N_i}|\dot f_i-\dot f_j|
\right)\right].
\]

The same componentwise box and slew projection used by the learning arms is then applied. The controller is local-neighbour, independently executed, and nonsmooth at zero because of the absolute-value features.

### 4.3 Learning arms and information-contract audit

Three learning arms share the direct-M/D action interface, training budget, seeds, development/evaluation access, actor/critic capacity, and checkpoint rule:

1. **Scalar TD3:** a fresh memoryless Yang-compatible engineering baseline using permitted local and adjacent measurements; it is not an exact reproduction of the SAC algorithm in [1].
2. **Nominal no-message mode-aware multi-agent TD3:** independently executed local actors whose neighbour slots are masked inside every actor path, with a training-time joint critic.
3. **Message-enabled mode-aware multi-agent TD3:** the same network dimensions with permitted neighbour measurements at execution.

Each actor receives a seven-slot row containing its scaled active power, frequency deviation, and RoCoF, followed by the frequency deviations and RoCoFs of its two ring neighbours. The nominal no-message arm keeps the same network input dimension and zeros the four neighbour slots. In the first execution this masking covered only behaviour-policy and evaluation calls: a post-hoc source audit found that replay stored the unmasked observation and that online and target actor updates consumed unmasked actor rows, so that execution was not a clean information ablation. The re-execution reported in Sec. 5.2 applies the mask inside every actor path, making the recorded arm difference a single-factor message contrast. Each actor is a two-hidden-layer multilayer perceptron with 256 units per layer and a two-dimensional tanh output. The training-only twin joint critic receives all four observation rows and all four action rows. Its output is scalar for scalar TD3 and two-dimensional for the common/differential arm.

For the mode-aware arms, the step costs are

\[
c_d=\frac{1}{3}\left\|\frac{T_d\Delta f}{0.15}\right\|_2^2
+\frac{1}{3}\left\|\frac{T_dP_{es}}{0.25}\right\|_2^2,
\]

\[
c_c=\frac14\sum_{i=1}^{4}\left(\frac{\Delta f_i}{0.15}\right)^2
+\frac14\sum_{i=1}^{4}\left(\frac{\operatorname{RoCoF}_i}{1.0}\right)^2.
\]

Under the frozen orthonormal frame (the mean direction plus the three differential rows of $T_d$), the common cost is not a pure common-mode quantity. Writing $c(x)=\operatorname{mean}\Delta f$ and $z=T_d\Delta f$, Parseval's identity gives
\[
\frac14\sum_{i=1}^{4}\left(\frac{\Delta f_i}{0.15}\right)^2
=\frac{c(x)^2}{0.15^2}+\frac{\|z\|_2^2}{4\cdot 0.15^2},
\]
and the RoCoF term decomposes identically, so $c_c$ charges differential frequency and RoCoF energy as well as the common mode: it is a common-protection surrogate that overlaps $c_d$ on the differential modes. Similarly, a per-step executed-action energy penalty $e=\operatorname{mean}_i\|a_i\|_2^2=\tfrac14\|A\|_F^2$ splits exactly into common-coordinated and differential action energy, $\tfrac14\|q_0^TA\|^2+\tfrac14\|T_dA\|^2$, so such a penalty taxes total action energy rather than a specific mode. These identities are exact under the frozen definitions and hold numerically on the recorded trajectories.

The actor combines the differential and common critic outputs using a projected multiplier initialized at 1.0 and updated after every episode as

\[
\lambda\leftarrow\operatorname{clip}
\{\lambda+0.05(\textstyle\sum_t c_c(t)-3),0,10\}.
\]

The scalar arm instead sums the four frozen V4 per-agent rewards, with weights $\phi_f=100$, $\phi_{abs}=50$, and $\phi_h=\phi_d=0.0056$. Its action-related terms penalize squared fleet-mean parameter changes rather than componentwise magnitude or variation, so differential actions can cancel in that term. The CD objectives contain no explicit penalty on action magnitude, RMS, total variation, or slew-limit use, and neither CD cost is identical to the registered physical endpoints and guard families. This is an objective-to-decision-contract mismatch, not evidence that the mismatch caused the measured degradation. All arms use Adam with learning rate $3\times10^{-4}$, discount 0.99, target-update coefficient 0.005, replay capacity 200,000, batch size 256, target-policy noise 0.2 clipped at 0.5, exploration noise 0.1, and an actor update every two critic updates. Evaluation is deterministic and uses final weights only; no best-checkpoint selection or evaluation-profile access occurs during training.

The original design intended the difference between arms 2 and 3 to estimate a runtime-message increment. In the first execution the nominal no-message arm masked neighbour slots at interaction and evaluation but not inside actor updates, so the recorded difference was descriptive only; the re-execution reported in Sec. 5.2 enforces the mask inside every actor path and yields the clean single-factor measurement. The comparison between arm 3 and arm 1 likewise does not isolate a single algorithmic cause. A second audit finding applies to all learned arms: the executed action is a stateful slew projection of the actor output, while the seven-slot actor observation omits the previous executed action and the actor/target objectives optimize unslewed outputs. This establishes an action-interface mismatch, not its causal contribution to the measured failure; a registered single-factor repair of exactly this interface is tested in Sec. 5.2.

### 4.4 Guard-first decision rule

For the learning canary, every seed-profile block must respect common-frequency integral, worst-unit peak, and RoCoF ceilings of 103% of the deterministic reference, and action-stress ceilings of 110%. A learner also needs positive seed-median improvement on both physical endpoints. Rewards, coordinate scores, or isolated favourable scenarios cannot override a guard failure. Three seeds support a bounded robustness description but not population-level statistical inference.

The auxiliary energy-port target region is

\[
\mathcal Q=\{r_d\le0.95,\ r_{\rm cross}\le1.10\},
\tag{5}
\]

with an additional strict cross check $r_{\rm cross}\le0.95$. Here $r_d$ and $r_{\rm cross}$ are ratios to the registered auxiliary references, not to the direct-$M/D$ learning comparator.

## 5. Results

### 5.1 A strong deterministic direct-M/D comparator

The development-selected local-neighbour law reduces off-diagonal response energy by 60.79% and disturbance-driven differential energy by 64.13% relative to zero action, while passing all development guards. This result establishes two facts. First, the physical endpoints are responsive to the direct-M/D interface at the registered finite amplitudes. Second, zero action is not a credible baseline for a learning claim.

On all four evaluation profiles, the outcome-seeing finite oracle selects the same law that was chosen on development data. Its incremental improvement over the deterministic law is therefore 0% for both endpoints, including leave-one-profile-out summaries. This is a strong comparator-risk signal, not a proof that the deterministic law is globally optimal.

A registered follow-up expands the law bank to 21 laws: a densified grid with inertia gains $\{0.5,1,1.5,2,3\}$ and damping gains $\{0.5,1,1.5,2\}$ plus one PI-type law. Development selection then moves to $(k_M,k_D)=(3,2)$, which reduces off-diagonal response energy by 63.87% and disturbance differential energy by 64.95% relative to zero action; the PI-type law is development-ineligible on the common-mode no-harm guard; and the outcome-seeing oracle again selects the development winner on all four evaluation profiles, so the incremental improvement remains 0% for both endpoints. The zero-headroom statement therefore covers the 21-law family, not only the original nine.

A separate preregistered study tests 350 fixed three-segment direct-M/D schedules without allowing evaluation-informed reselection. Development-only selection yields a unique schedule that is guard-clean on both development profiles. Applied unchanged to four fixed evaluation profiles, it is guard-clean on two: the other two fail respectively because action total variation exceeds its no-harm bound and because the differential-energy improvement is 4.85%, below the frozen 5% threshold. This establishes a partial finite-bank transfer witness for the larger piecewise-schedule class; two passes among four fixed profiles are descriptive and do not estimate a transfer probability.

### 5.2 The tested MARL arms do not improve the comparator

All nine training runs finish their 43,200 interaction steps with no missing seed. The physical evaluation comprises 40 JSON files containing 240 trajectories: 216 learning trajectories and 24 deterministic-reference trajectories. Nevertheless, all 36 learning arm-seed-profile blocks violate both the common no-harm and action-stress guards.

| Controller | Median off-diagonal ratio vs. deterministic | Median differential-energy ratio vs. deterministic | Guard result |
|---|---:|---:|---|
| Scalar TD3 | 3.90 | 2.97 | Fail |
| Nominal no-message mode-aware MATD3 (repaired mask) | 2.95 | 2.01 | Fail |
| Mode-aware MATD3, runtime messages | 5.26 | 2.54 | Fail |

The deterministic evaluation reference has aggregate off-diagonal energy $3.43\times10^{-4}$ and disturbance differential energy $2.21\times10^{-3}$, bit-identical across both executions. Every learning median is worse on both endpoints. With the information contract repaired, the message-enabled arm's seed-median difference versus the matched no-message arm is $-78.43\%$ off-diagonal and $-26.74\%$ differential improvement, where a positive value would indicate improvement. This is a clean single-factor contrast within the tested bundle: runtime neighbour messages add no positive coordination increment, and both arms still fail every physical guard. A five-seed extension of this bundle passes its preregistered bit-repro gate (a fresh gate run reproduces the stored checkpoint byte-for-byte, and the frozen three-seed verdict over the reused checkpoints reproduces the stored guard profile to the block) and keeps the five-seed-median improvement strongly negative at $-74.98\%$ off-diagonal / $-35.49\%$ differential, while disclosing the dispersion the three-seed median hid: the matched no-message arm carries a 3.81$\times$ off-diagonal per-seed spread (one seed at 0.0036688 versus the 0.0010094 median) against 1.84$\times$ for the message arm and 1.77$\times$ for the scalar arm.

A probe-amplitude ladder re-evaluates the same frozen checkpoints at probe-magnitude factors $\{0.5,0.7,1.0,1.3,1.5\}$: the guard-failure verdict holds at every amplitude, and the amplitude-1.0 bank is bit-identical to the recorded execution. The learning-versus-deterministic endpoint-ratio magnitudes are amplitude-sensitive (11 of 18 arm–seed–endpoint cells drift beyond 20% across the ladder), so the exact ratios in the table are registered-grid values; the qualitative verdict and the negative message increment (sign-stable at factors 0.7–1.5 off-diagonal and at all factors differential, peaking at the registered amplitude) do not depend on that choice.

A registered single-factor repair then tests the leading mechanism hypothesis: the actor state gains the previous executed (post-slew) action, and the target and online actor paths evaluate the same post-projection quantity the environment executes, with everything else frozen. Under this bundle the message arm's three-seed-median endpoint ratios versus the deterministic reference drop to 0.6954 off-diagonal and 0.7104 differential (from 5.2569 / 2.5427)—the first time a learning arm beats the strong deterministic reference on both endpoints—the no-message arm reaches 1.2297 / 0.9547, and the message increment over the matched no-message arm flips to a clean positive $+43.45\%$ / $+25.59\%$. Zeroing the added feature degrades the CD arms' endpoints by up to $+1.12$ relative (the scalar arm stays near zero), confirming the policies consume the feature. The canary verdict does not flip: every block still violates the action-stress guards and a subset of the common no-harm guards, which localizes the residual failure to the objective-to-decision-contract gap—the CD objective carries no action-effort or no-harm terms.

Two registered objective-repair rounds then test whether the residual gap is a missing action-effort term. Adding the frozen executed-action energy term (weight $1.0$) to the differential channel regresses the message arm's endpoint ratios to 2.3641 off-diagonal / 1.9440 differential (from 0.6954 / 0.7104), flips its message increment negative ($-35.25\%$ / $-34.02\%$), and worsens the no-harm profile (common-frequency failures 19 to 36 blocks, worst-peak 28 to 34), while the scalar arm stays bit-unchanged. Moving the identical term to the common channel does not flip the canary either: the common Lagrange multiplier saturates at its 10.0 ceiling in all six runs (median $\approx 0$ under the two earlier bundles), worst-peak failures reach 36 and RoCoF 26, endpoints stay at 2.3999 / 1.6625, and the message increment returns positive but below the unpenalized value ($+21.16\%$ / $+7.56\%$). A bit-non-perturbing diagnostic rerun of the pre-repair bundle records the training-side counterpart: critic loss grows 24–126$\times$ between the first and last training quartiles, the TD-error spread grows 4.9–11.3$\times$, actor gradient norms vanish in five of six runs, and the common budget never binds.

The modal identities of Sec. 4.3 explain why neither placement is modal routing. The penalized objective differs across the two rounds by $(\lambda-1)J_e$—the effort coefficient is the fixed $1.0$ in the differential placement but the learned multiplier $\lambda$ in the common placement—plus a critic-head reassignment; and because the dual update reads the modified cost, the effort also consumes the common episodic budget of 3.0 in the common placement, so a budget-satisfying episode implies mean executed-action energy of at most 0.1 per step. Both placements are therefore theory-neutral as channel choices: the measured difference is an effective-regularization-weight and budget effect, not evidence that the effort belongs to a physical mode.

The guard failures are likewise consistent with constrained-MDP theory. The dual ascent constrains an expected episodic quadratic surrogate, while the canary demands trajectory-level, reference-relative peak, integral, action-RMS, and total-variation ceilings on every profile–seed block; the action-stress statistics are absent from the constraint entirely, the actor's common critic is discounted ($0.99$) while the dual residual is an undiscounted 30-step sum, and the training feasible set has no proven inclusion into the guard set [13]–[15]. Minimizing the training objective therefore cannot by itself purchase guard compliance, and the combination of improved endpoints with 36/36 action-stress failures is the expected behaviour of this constraint hierarchy rather than a paradox.

Measured against the modal decomposition, the executed actions are differential-dominant in every penalized bundle: three-seed-median differential action-energy fractions move from 0.358 (message arm) and 0.458 (no-message arm) under the unpenalized bundle to 0.665–0.731 and 0.750–0.821 under the two penalized bundles, while the scalar arm holds at 0.837 across all rounds. Both effort placements therefore tax predominantly differential action energy, and the two rounds differ as effective-regularization-weight and budget interventions rather than as modal routing.

A value-estimation repair then tests the training-side layer: a frozen critic gradient clip (max-norm $1.0$) on the CD arms. The canary still does not flip, but the round records the family's first no-harm guard gains (RoCoF failures 26 to 22 blocks, worst-peak 36 to 35), moves both CD arms toward the reference (message arm 2.3999 to 1.7756 off-diagonal ratio; no-message arm 3.0441 to 1.5603), damps the critic-loss growth between training quartiles from the unclipped 24–126$\times$ (pre-repair bundle) to 5.0–8.0$\times$ without reaching the preregistered $3\times$ stopping threshold, and keeps the scalar arm byte-identical — bounded critic updates steer a better-behaved but still guard-failing policy, the divergence is damped rather than stopped, and the invariant action-stress failures remain consistent with the constraint-hierarchy diagnosis.

A guard-aligned constraint round then writes the action-stress statistics directly into the training objective: the CD actor objective gains the executed-action squared energy and the absolute step-to-step action change (the guard RMS and total-variation statistics, computed on the same post-slew trace the guards read), each with a per-episode projected multiplier (step $0.05$, ceiling $10.0$) updated on the reference-relative residual against frozen deterministic thresholds, on the unpenalized reward seam. The canary still does not flip: the action-stress guards stay 36/36 failed blocks, unchanged across all five rounds of the family. The round exposes an implementation defect instead of a mechanism verdict: in the sealed learner the constraint terms enter inside the actor-loss negation, so gradient descent maximizes the action-energy and total-variation statistics, the dual ascent self-reinforces every multiplier to its $10.0$ ceiling (all 240 retained values) with RMS residuals 38.3–90.8$\times$ above the thresholds, and both CD actors pin roughly 90% of action components at the actuator bounds (slew-saturation fraction median $0.90$ across the 36 blocks; a saturation-budget guard that never failed before now fails 24/36 blocks). The same maximal-actuation policy nevertheless yields the family's best common no-harm profile — common-frequency failures 36 to 12, RoCoF 22 to 14, worst-peak 35 to 24 — and drains the common multiplier to zero in 6/6 runs, while the message-arm endpoints regress to 2.3419 / 1.7751 against the deterministic reference (0.6954 / 0.7104 under the unpenalized base), the message increment collapses to 0.0000 with both CD arms bit-identical, and the critic divergence persists (Q4/Q1 5.98–9.61). Because the slew clip flattens any maximal-actuation policy into the same executed sequence, the zero message increment only shows that the message contrast is masked by clipping this round and carries no verdict on communication value; the guard-aligned constraint itself remains untested pending a sign-corrected retest.

A sign-corrected retest then runs the identical bundle with the two constraint terms moved outside the actor-loss negation (penalty semantics), everything else verbatim. The preregistered key contrast is met: both action-stress guards move 36 to 12 failed blocks (24 of 36 blocks now pass each guard) — the first guard-level action-stress movement of the five-round family — confirming the sign defect as the explanation of the previous null. The correction is capped rather than complete: every retained multiplier still sits at its $10.0$ ceiling in 6/6 runs while the RMS residuals collapse from 38.3–90.8$\times$ to 1.1–10.1$\times$ (median 2.9–4.2), so the constraint narrows the action-stress gap without closing it, and no arm passes all guards. The bang-bang collapse resolves (CD saturation fraction 0.125–0.132 versus 0.90, execution mismatch 0.006 versus 0.366), the message contrast unmasks to a measured $-1.94\%$ / $-2.36\%$ versus the matched no-message arm (versus the clipping-masked 0.0000 and the unpenalized-base $+43.45\%$ / $+25.59\%$), the endpoints sit at 2.7477 / 2.1127 against the deterministic reference (0.6954 / 0.7104 unpenalized), the common no-harm profile reverts to 36/14/36 (versus 12/14/24 under maximal actuation), and the critic divergence persists (Q4/Q1 4.65–6.29). The scalar isolation arm remains byte-identical to the base bundle.

A critic-normalization round then layers the sign-corrected constraints with a PopArt-style running mean/std normalization of the CD-arm differential-channel TD target (decay $10^{-3}$, floor $10^{-4}$, common channel verbatim). The preregistered criterion is met: the original-scale critic divergence is suppressed (Q4/Q1 0.32–1.75 $<3$ across six runs, versus 4.65–6.29), the normalized loss stays of order one, and the untouched scalar arm still diverges (raw 3.5–7.0, byte-identical) — the value-estimation layer is repaired where applied. The repair cascades to the actor: the log-gradient norms stop vanishing and the action-stress no-harm guards stop failing across all 36 CD blocks (12/36 previously), even though the guard-aligned dual stays ceiling-capped (multiplier $10.0$ in 6/6, residuals 2.6–5.4$\times$). The canary still fails because the common-frequency and worst-peak no-harm guards fail in every block; endpoints remain 3.1–3.4$\times$ above the unpenalized base with a mixed-sign $\approx$0 message increment, so the residual is frequency restoration rather than action stress or value scale.

The owner-ordered C1-SAC round then reproduces the exact Yang-2022 TPWRS SAC interface — one independent per-agent SAC (single critic plus a soft value target, automatic entropy coefficient, four hidden layers of 128 units, no gradient clipping, no slew projection, reward Eq. 14–18 rebuilt from the observation row with weights 100/1/1 and no absolute-frequency term) — on the matched harness bundle. It measures a bounded negative result: the paper-strict reward diverges the value scale (critic loss $\sim 10^8$), saturates the entropy coefficient at its ceiling, collapses the policy entropy (mean log-probability $+10.4$ to $+10.9$), and the unslewed actions violate the actuator slew guard in every block, so the bank is invalid; the scalar arm stays byte-identical to the base, confirming the failure belongs to the interface rather than the harness, and the endpoints land 4.7–5.7$\times$ the deterministic reference — worse than the repaired CD family. This turns the manuscript's engineering-baseline caveat into a direct same-harness comparison.

This result supports a canary-level stop. A read-only audit supplies four relevant design facts: the historical nominal no-message execution masked neighbour slots at interaction and evaluation but not inside actor updates, and its repair is the single-factor change of the re-execution reported above; learned execution uses a stateful slew map absent from the actor state and target optimization; the CD objectives omit explicit action-effort and slew-use penalties; and their training costs do not coincide with the complete physical decision contract. The retained final-20 multiplier traces are numerically small and touch zero, while the evaluated CD actions are more stressed than the deterministic reference. These observations expose implementation and objective risks, but they do not isolate a cause. The scalar arm also fails under a different reward containing cancellable fleet-mean action terms, and the available records do not distinguish critic or replay error, inadequate optimization, broader partial observability, credit assignment, decoder conditioning, or limited incremental direct-M/D headroom. Completion of the fixed interaction budget is therefore not a convergence certificate. Nor does the canary show that longer training would necessarily fail, that SAC would match TD3, or that all MARL architectures are inferior to classical control. Because it fails before the preregistered expansion gate, no five-seed held-out learning comparison is claimed; the five-seed extension reported above is a training-seed statistical upgrade of the same nominal-connectivity bank, not the held-out expansion gate.

### 5.3 Homogenization intuition is insufficient in the nonlinear DAE

Proposition 1 motivates homogeneous effective $M$ and $D$ in an ideal model. A direct-M/D static homogenization diagnostic was therefore evaluated across eight disclosed canary profiles. It fails the physical gate: relative to the dynamic deterministic reference, the aggregate off-diagonal and differential ratios are 2.2229 and 2.7656. Common-integral, worst-unit peak, and worst-unit RoCoF ratios are 1.4166, 1.6630, and 1.3225 against a 1.03 ceiling, and action RMS is 1.7186 against a 1.10 ceiling.

This is not a contradiction of Proposition 1. The diagnostic includes finite-time ramping, heterogeneous operating profiles, a nonlinear DAE, parameter limits, and guards that are absent from the theorem. It instead shows why a reduced-model structural condition is not sufficient for acceptable finite-window closed-loop performance.

### 5.4 A structured energy-port controller passes development and unseen gates

The auxiliary experiment applies a frozen 0.4-Hz ring-edge bandpass controller with damping ratio $\zeta=0.35$ through the feasibility-native energy port. Its normalized action sum remains zero to numerical precision, with $\|\Sigma_v\|_2\le5\times10^{-17}$. The physical headroom map introduces state-dependent common-port leakage. For $K\le0.1$, that leakage scales approximately as $3.26\times10^{-4}K^2$ and is too small to explain the roughly 0.19 differential-ratio offset; the higher-gain regime follows a different, approximately linear scaling.

| Auxiliary controller and split | $r_d$ | $r_{\rm cross}$ | $\mathcal Q$ | Guards |
|---|---:|---:|---|---|
| Bandpass, $K=3.5$, development | 0.938947 | 0.539791 | Enter | Pass |
| Bandpass, $K=4.0$, development | 0.911541 | 0.515282 | Enter | Pass |
| Fixed blend B1, development | 0.874281 | 1.664997 | Miss cross | Pass |
| Time-varying blend E1, development | 0.961880 | 0.980770 | Miss differential | Pass |
| Frozen bandpass, $K=3.5$, unseen | 0.938218 | 0.793730 | Enter | Pass |

Both development gains satisfy (5), pass the stricter $r_{\rm cross}\le0.95$ check, and pass all guards. The earlier apparent small-gain anomaly is also resolved: the bandpass replaces rather than augments the local auxiliary reference, so $K\rightarrow0$ converges to zero action, not to the local controller. The measured anchor $r_d(0)=1.202733$ equals the zero-action-to-local-reference ratio, and the response changes smoothly for small positive gain.

The $K=3.5$ controller is then frozen without retry, tuning, or algorithm change. All 30 unseen-bank records complete, and the controller passes both endpoints, the stricter cross check, and every guard. The differential endpoint transfers almost exactly from development (0.938947 to 0.938218); the cross ratio rises from 0.539791 to 0.793730 but remains comfortably inside both cross ceilings.

Two registered robustness extensions bound the constructive result. On a frozen 12-variant topology bank (nominal, six single-line outages of the two inter-area corridors and the two VSG tie lines, and five tie-reactance scalings), the frozen $K=3.5$ controller passes both endpoints and every guard on all 10 variants whose equilibrium passes the registered eigenvalue hard gate ($r_d\in[0.9296,0.9398]$, $r_{\rm cross}\in[0.4530,0.6889]$, the stricter cross check included); opening either VSG tie line diverges at initialization and is excluded by that gate, and the nominal variant reproduces the development endpoints within $7\times10^{-7}$ relative. On a three-block unseen condition bank it passes the new-conditions block ($r_d=0.9323$, $r_{\rm cross}=0.9108$) and the stiff-plant block with inertia $\times1.15$ and damping $\times0.85$ ($r_d=0.9080$, $r_{\rm cross}=0.7300$), and fails the differential ceiling on the relaxed-plant block with inertia $\times0.85$ and damping $\times1.15$ ($r_d=0.9712>0.95$, all guards passing), scoping the constructive claim to exclude that plant perturbation. A pre-registered breadth check with the second disclosed gain $K=4.0$ (its own first use of the same blocks) passes the new-conditions block ($r_d=0.9040$, $r_{\rm cross}=0.8512$) and the stiff-plant block ($r_d=0.8750$, $r_{\rm cross}=0.6716$) and improves the relaxed-plant block to $r_d=0.9506$, still exceeding the 0.95 ceiling by 0.06% with every guard passing; both disclosed gains therefore share the relaxed block as their boundary, and no further gain is evaluated on these blocks.

This result refutes the statement that every finite-order linear controller must fail for this controller class and these banks. It does not validate MARL, and it establishes neither topology generalisation nor a population guarantee. The direct-M/D and energy-port ratios also use different estimators and references; their percentages must not be numerically combined.

## 6. Discussion

### 6.1 What the combined evidence says

The experiments do not support an “exact decoupling is impossible” paper. They support a more specific and more useful conclusion. Direct dynamic adjustment of virtual inertia and damping is a difficult tested interface for learning decoupling-oriented behaviour: exact separation is structurally restrictive in the ideal model, zero-bias dynamic parameter feedback has no additional local first-order Jacobian authority in the stated multiplicative reduction, a strong deterministic law exhausts the registered static/PI bank while a separately sealed 350-schedule class contains one partial-transfer witness, and the tested learners move far outside the comparator's safe performance region. The repaired nominal no-message information contract shows that providing runtime neighbour messages adds no positive coordination increment within the tested bundle.

At the same time, the structured energy-port result shows that the joint target is not empty for a distinct control object and that its development candidate transfers to a previously unseen bank. It cannot be ranked numerically against the direct-M/D canary because the actuator, estimator, headroom map, window, bank, and reference differ. The defensible interpretation is therefore not “traditional algorithms always beat MARL,” or even that action-basis mismatch caused the canary failure. The registered slew-state repair shows that the representation factor was the endpoint blocker: with the executed action restored to the actor state and target semantics aligned, the CD arms reach 0.70–1.23 times the deterministic reference and the message increment turns positive, while every block still violates the action-stress guards. The two objective-repair rounds then show the gap is not a missing action-effort term in either channel: the differential placement trades decoupling response for action regularization, and the common placement saturates the no-harm budget without guard gain; under the modal identities of Sec. 4.3 both are effective-weight and budget interventions rather than modal routing. The diagnostic rerun adds the training-side counterpart—critic divergence with vanishing actor gradients on the pre-repair bundle. The residual failure therefore concentrates in a two-layer structure: a constraint hierarchy whose first direct implementation entered the constraint terms with a reward sign and self-reinforced to saturation against an output-locked policy, whose sign-corrected retest reaches the guard layer (both action-stress guards 36 to 12) while the multiplier ceiling caps the correction short of closure, and whose follow-up critic normalization suppresses the divergence (original-scale Q4/Q1 0.32–1.75, threshold 3 met), stabilizes the actor gradients, and stops the action-stress guard failures across all 36 blocks; and a frequency-restoration layer — the common-frequency and worst-peak no-harm guards that still fail in every block with endpoints 3.1–3.4$\times$ above the unpenalized base — which the value-estimation repair does not by itself close. The exact Yang SAC reproduction further sharpens this: on the same harness the paper's own interface collapses (value divergence, entropy collapse, slew violation) and lands worse than the repaired CD family, so the negative result is a property of the tested interface-and-reward on this physics, not of MARL in general.

### 6.2 Why the negative learning result remains publishable

The negative result is informative because it is tied to a strong comparator, physical endpoints, hard guards, and an explicit audit of failed identification. It answers two bounded questions. The tested MARL implementation bundle does not beat the deterministic direct-M/D controller, and training reward cannot be substituted for the registered decoupling metrics. It also records that the intended message contrast, once the information contract was repaired, is a cleanly measured negative single-factor comparison. The constructive unseen-bank result further prevents overgeneralization by demonstrating that the joint target is nonempty for a separate structured object.

A conference claim should remain at this evaluation level. The work does not justify statements that MARL is fundamentally unsuitable for power systems, that the original SAC method in [1] fails, or that a model-based controller is universally superior. It also cannot claim topology generalisation, electromagnetic-transient validity, hardware-in-the-loop performance, real-time implementation, or field deployment. Consistent with the registered scope decision, larger-grid performance and cross-network policy transfer are reserved for follow-up research rather than claimed here.

### 6.3 Non-pooled evidence from distinct formulations

Three separately registered studies on related modified-Kundur formulations provide mechanism-level triangulation. They are not replications of Object A or Object B, and their records are not pooled with the main results.

| Supporting formulation | Bounded observation | Relevance and non-transfer boundary |
|---|---|---|
| Three executed zero-sum edge actions, 24 sealed scenarios, five training seeds per learned architecture | A selected classical edge controller improves synchronization loss by 16.46% and fast inter-area IAE by 3.27% versus zero residual. Neither a joint-observation actor nor a neighbour-only distributed actor clears both primary gates relative to that controller; both fail the relative tail no-harm guard. | Independently supports the risk of claiming neural increment over a strong structured comparator. It does not test four independently actuated VSGs or direct M/D actions. |
| Offline common-plus-edge response-space feasibility, 16 exposed cases | Adding one fleet-common power direction to a three-edge zero-sum basis increases feasible cases from 10/16 to 16/16 while meeting the registered common and differential targets. | Supports the action-basis mechanism. It has no nonlinear trajectory, causal information map, implemented controller, or learning result. |
| Outcome-seeing residual schedules on a constrained energy port, ten development conditions | A finite noncausal selector reduces disturbance differential energy to 0.818 of a local reference, while both probe-cross ratios remain exactly 1.0. | Shows that disturbance damping alone is not joint decoupling. It is nondeployable and not an upper bound over causal controllers. |

The convergence is qualitative: strong classical structure repeatedly creates a difficult comparator, the available spatial action directions determine which modal objectives are reachable, and success on one frequency endpoint does not imply reduced off-diagonal response. Because the information patterns, action bases, scenario banks, and actor definitions differ, these studies cannot be used to enlarge the sample size or strengthen the main confidence claims.

### 6.4 Implications for future controller design

The next defensible method should preserve the successful structure rather than restart an unconstrained algorithm sweep. One option is a baseline-anchored residual architecture: the verified low-order energy-port controller supplies guard-passing differential damping on the registered banks, while a small learned residual addresses model mismatch under hard action and no-harm projection. Runtime information could be expressed as graph differences or edge flows instead of asking a large neural network to subtract nearly common absolute frequency signals.

A second direction is a finite-impulse-response Youla or system-level-synthesis search around a stable baseline. For a fixed linear model and valid closed-loop response parameterization, finite-window trajectories can be affine in the response variables and energy bounds can become convex quadratic or second-order-cone constraints. However, the available demonstration solver is only a blueprint: it does not establish a valid robust Youla parameterization for the nonlinear headroom map, internal stability of the implemented DAE closed loop, or a formal dual infeasibility certificate. Those conditions must be proved before the solver can support a controller-class impossibility claim.

A third direction follows directly from the constraint-hierarchy diagnosis: keep the differential primary objective, but replace the single common surrogate with guard-aligned constraints—an action-RMS constraint and a total-variation constraint whose statistics, units, and aggregations match the guards exactly, each with its own projected multiplier updated on the episode residual [13]–[15]—and stabilize the value estimates so the multipliers steer a well-conditioned policy rather than a diverging critic. The guard-aligned constraint rounds of Sec. 5.2 now measure both halves: the first attempt never tested the mechanism as designed (the constraint terms were implemented with a reward sign and the multipliers self-reinforced to their ceiling while the actors stayed pinned at the actuator bounds), the sign-corrected retest shows a real but ceiling-capped effect (the action-stress guards move 36 to 12 with the residuals tenfold closer to the thresholds, yet every multiplier stays at its ceiling and no arm passes all guards), and the critic normalization then suppresses the divergence and closes the action-stress guard gap across all 36 blocks — confirming that value-estimate stability is the enabling repair rather than an optional companion, while the remaining common-frequency and worst-peak no-harm failures mark the open axis, with a multiplier-ceiling or schedule sweep still an open option.

## 7. Threats to Validity and Limitations

**Fixed model and simulator.** The evidence covers one modified Kundur topology family in one phasor-domain simulator: the frozen 12-variant bank of single-line outages and tie-reactance scalings is tested (Sec. 5.4), while combined (N-2) outages, other lines, and larger grids remain outside scope. The variant bank is evaluated only for the constructive energy-port controller; the learning arms are assessed solely on the nominal connectivity, so their guard profile under topology perturbations is untested and the constructive controller's robustness does not transfer to them. Network balance, converter inner loops, measurement delays, switching dynamics, and protection interactions are outside scope.

**Finite scenario banks.** The deterministic and learning conclusions are finite-bank statements. The outcome-seeing oracle ranges over the registered static/PI law banks (nine laws, extended to 21 with a PI-type law in a registered follow-up), so their zero-headroom result is confined to those families. A separate 350-member piecewise-schedule family yields one development-selected schedule that passes every registered guard on two of four fixed evaluation profiles; the two-of-four count is not a probability because the profiles were fixed rather than sampled from a declared population. The energy-port controller passes one development and one unseen bank; on the frozen robustness extensions it passes all sound topology variants and two of three unseen condition blocks, with both disclosed gains sharing the failing relaxed-plant block as their boundary, which bounds rather than generalizes the claim.

**Limited learning inference.** The registered canary is characterized on three seeds per arm; the five-seed training extension of the R410 bundle (Sec. 5.2) strengthens the median-level negative message contrast but remains descriptive statistics rather than population inference (the matched no-message arm's per-seed off-diagonal spread is 3.81$\times$). No claim is made about a five-seed title-positive learning test because the preregistered expansion condition was not met. The 36 profile blocks are repeated conditions nested within nine trained policies, not 36 independent training replications.

**Causal diagnosis and retained logs.** Only the final 20 episode-level common costs and multiplier values are retained. Complete return histories, actor/critic losses, Bellman residuals, gradient and parameter-update norms, replay-coverage diagnostics, and held-out critic calibration are unavailable. The original no-message execution consumed unmasked replay observations inside actor updates; the repaired re-execution reported in Sec. 5.2 enforces the mask in every actor path, so the message contrast is a clean single-factor measurement, while the absolute comparison between the two executions remains two-factor because the earlier training ran under the pre-repair slew projector. The stateful slew memory was absent from the actor state in the original bundle; the registered repair (Sec. 5.2) adds it and is measured to flip the endpoints without flipping the guard verdict. Complete per-update diagnostic curves exist only for the pre-repair bundle; their transfer to the repaired bundles is a hypothesis bounded by the registered repair rounds, which retain a per-update critic-loss proxy instead. The action-stress guards read the normalized executed actions—the same trace the effort penalty uses—and a dedicated round that charges those statistics (RMS, total variation, reference-relative ceilings) leaves the action-stress guards unchanged because its constraint terms enter the loss with a reward sign and its multipliers saturate while the actors stay pinned at the actuator bounds; the sign-corrected retest then moves both action-stress guards 36 to 12 failed blocks while every multiplier still sits at its ceiling with residuals roughly tenfold closer to the thresholds, so the measured correction is capped rather than complete; the critic normalization then suppresses the divergence (per-update critic-loss proxies now retained on both the normalized and reconstructed original scale, original-scale Q4/Q1 0.32–1.75) and stops the action-stress guard failures across all 36 blocks, leaving the common-frequency and worst-peak no-harm guards as the remaining failure class. Consequently, valid completion of 43,200 interaction steps per arm--seed run establishes neither convergence nor nonconvergence, and the observed action stress cannot identify its own cause. The preserved post-hoc source copy also lacks complete immutable post-amendment execution provenance, so these implementation findings are reported as audit limitations rather than historical causal effects.

**Algorithm identity.** The scalar TD3 arm is Yang-compatible in control object and information permissions but is not a strict reproduction of the multi-agent SAC implementation in [1]. The owner-ordered exact reproduction (Sec. 5.2) instantiates that interface verbatim on this harness and measures an invalid bank (value divergence, entropy collapse, slew violation under the declared no-slew contract), so no SAC-advantage claim is possible from this bundle; conclusions must name the tested algorithms.

**Model-theory gap.** Proposition 1 and Lemma 1 are explanatory reduced-model results. In particular, the actual reduced DAE input Jacobian $B_{u,r}=f_u-f_yg_y^{-1}g_u$ has not been identified. The DAE, nonsmooth policy features, asymmetric decoder, saturation, and sampled execution therefore prevent these results from serving as a full nonlinear impossibility certificate or an established cause of the measured learning failure.

**Action-object separation.** The constructive energy-port experiment and the direct-M/D learning experiment use different actuators, estimators, headroom maps, banks, windows, and references. They motivate a future matched mechanism comparison but do not presently identify an action-basis cause or support a pooled numerical ranking.

## 8. Conclusion

This paper evaluates decoupling-oriented MARL coordination of four parallel VSG proxies under a physical, guard-first protocol. A deterministic local-neighbour direct-M/D controller provides a strong baseline, reducing both registered endpoints substantially relative to zero action. A finite outcome-seeing oracle finds no additional headroom within the same law bank. Under fixed budgets and three seeds, scalar TD3, nominal no-message mode-aware MATD3, and message-enabled MATD3 all worsen both physical endpoints and violate common-mode and actuator guards. Under the repaired information contract, the message arm's measured three-seed-median increment over the matched no-message arm is negative on both endpoints (78.43% off-diagonal and 26.74% disturbance differential), so runtime neighbour messages add no positive coordination increment for this bundle.

The later piecewise-schedule study sharpens the finite-family boundary rather than reversing the learning result: one schedule selected without evaluation access passes all guards on two of four fixed evaluation profiles, while its two explicit failures remain part of the claim. This is evidence that the direct-M/D schedule class contains a bounded partial-transfer witness, not evidence of a 50% transfer rate, topology generalisation, learner discoverability, stability, or safety.

These results do not make decoupling impossible. Reduced-model analysis identifies structural limits of exact separation and local dynamic M/D feedback, while a separate structured energy-port bandpass controller enters the joint development target region and passes a one-use unseen bank. The central lesson is therefore bounded: the tested direct-M/D MARL bundle fails a physically guarded comparison, while a distinct structured object establishes that the joint target itself is attainable on its registered banks. A registered slew-state repair flips the endpoints without flipping the guard verdict, localizing the residual failure to the objective-to-decision-contract gap; the evidence does not rank the remaining optimization and credit-assignment effects. If a stronger mechanism claim is pursued after this conference draft, the next discriminating mathematical evidence would be a matched DAE and finite-horizon authority calculation; any renewed learning study would require a fresh, preregistered, single-factor intervention with complete diagnostics rather than an algorithm sweep.

## References

[1] Q. Yang, L. Yan, X. Chen, Y. Chen, and J. Wen, “A distributed dynamic inertia-droop control strategy based on multi-agent deep reinforcement learning for multiple paralleled VSGs,” *IEEE Transactions on Power Systems*, vol. 38, no. 6, pp. 5598–5612, 2023, doi: [10.1109/TPWRS.2022.3221439](https://doi.org/10.1109/TPWRS.2022.3221439).

[2] S. Fu, Y. Sun, Z. Liu, X. Hou, H. Han, and M. Su, “Power oscillation suppression in multi-VSG grid with adaptive virtual inertia,” *International Journal of Electrical Power & Energy Systems*, vol. 135, art. 107472, 2022, doi: [10.1016/j.ijepes.2021.107472](https://doi.org/10.1016/j.ijepes.2021.107472).

[3] S. Fu, Y. Sun, L. Li, Z. Liu, H. Han, and M. Su, “Power oscillation suppression of multi-VSG grid via decentralized mutual damping control,” *IEEE Transactions on Industrial Electronics*, vol. 69, no. 10, pp. 10202–10214, 2022, doi: [10.1109/TIE.2021.3139197](https://doi.org/10.1109/TIE.2021.3139197).

[4] J. W. Simpson-Porco, Q. Shafiee, F. Dörfler, J. C. Vasquez, J. M. Guerrero, and F. Bullo, “Secondary frequency and voltage control of islanded microgrids via distributed averaging,” *IEEE Transactions on Industrial Electronics*, vol. 62, no. 11, pp. 7025–7038, 2015, doi: [10.1109/TIE.2015.2436879](https://doi.org/10.1109/TIE.2015.2436879).

[5] Q. Shafiee, J. M. Guerrero, and J. C. Vasquez, “Distributed secondary control for islanded microgrids—A novel approach,” *IEEE Transactions on Power Electronics*, vol. 29, no. 2, pp. 1018–1031, 2014, doi: [10.1109/TPEL.2013.2259506](https://doi.org/10.1109/TPEL.2013.2259506).

[6] Y. Li, W. Gao, W. Yan, S. Huang, R. Wang, V. Gevorgian, and D. W. Gao, “Data-driven optimal control strategy for virtual synchronous generator via deep reinforcement learning approach,” *Journal of Modern Power Systems and Clean Energy*, vol. 9, no. 4, pp. 919–929, 2021, doi: [10.35833/MPCE.2020.000267](https://doi.org/10.35833/MPCE.2020.000267).

[7] O. Oboreh-Snapps, B. She, S. Fahad, H. Chen, J. W. Kimball, F. Li, H. Cui, and R. Bo, “Virtual synchronous generator control using twin delayed deep deterministic policy gradient method,” *IEEE Transactions on Energy Conversion*, vol. 39, no. 1, pp. 214–228, 2024, doi: [10.1109/TEC.2023.3309955](https://doi.org/10.1109/TEC.2023.3309955).

[8] S. Kang, Y. Jung, D. You, and G. Jang, “Enhancing frequency stability with decentralized adaptive control using multi-agent deep reinforcement learning of multi-VSGs,” *International Journal of Electrical Power & Energy Systems*, vol. 172, art. 111374, 2025, doi: [10.1016/j.ijepes.2025.111374](https://doi.org/10.1016/j.ijepes.2025.111374).

[9] R. Gorsane, O. Mahjoub, R. J. de Kock, R. Dubb, S. Singh, and A. Pretorius, “Towards a standardised performance evaluation protocol for cooperative MARL,” in *Advances in Neural Information Processing Systems*, vol. 35, pp. 5510–5521, 2022. [Online]. Available: [NeurIPS proceedings](https://proceedings.neurips.cc/paper_files/paper/2022/hash/249f73e01f0a2bb6c8d971b565f159a7-Abstract-Conference.html).

[10] G. Dulac-Arnold, N. Levine, D. J. Mankowitz, J. Li, C. Paduraru, S. Gowal, and T. Hester, “Challenges of real-world reinforcement learning: definitions, benchmarks and analysis,” *Machine Learning*, vol. 110, no. 9, pp. 2419–2468, 2021, doi: [10.1007/s10994-021-05961-4](https://doi.org/10.1007/s10994-021-05961-4).

[11] J. Schiffer, R. Ortega, A. Astolfi, J. Raisch, and T. Sezi, “Conditions for stability of droop-controlled inverter-based microgrids,” *Automatica*, vol. 50, no. 10, pp. 2457–2469, 2014, doi: [10.1016/j.automatica.2014.08.009](https://doi.org/10.1016/j.automatica.2014.08.009).

[12] L. Wang, T. Li, X. Hu, Z. Cheng, and B. Zhang, “Power decoupling control of paralleled virtual synchronous generators based on virtual complex impedance,” *Energy Reports*, vol. 9, suppl. 12, pp. 43–47, 2023, doi: [10.1016/j.egyr.2023.09.140](https://doi.org/10.1016/j.egyr.2023.09.140).

[13] J. Achiam, D. Held, A. Tamar, and P. Abbeel, “Constrained policy optimization,” in *Proc. 34th Int. Conf. Machine Learning (ICML)*, PMLR 70:22–31, 2017.

[14] Y. Chow, M. Ghavamzadeh, L. Janson, and M. Pavone, “Risk-constrained reinforcement learning with percentile risk criteria,” *Journal of Machine Learning Research*, vol. 18, no. 167, pp. 1–51, 2018.

[15] A. Stooke, J. Achiam, and P. Abbeel, “Responsive safety in reinforcement learning by PID Lagrangian methods,” in *Proc. 37th Int. Conf. Machine Learning (ICML)*, PMLR 119:9133–9143, 2020.

[16] F. Paganini and E. Mallada, “Global analysis of synchronization performance for power systems: Bridging the theory-practice gap,” *IEEE Transactions on Automatic Control*, vol. 65, no. 7, pp. 3007–3022, 2020, doi: [10.1109/TAC.2019.2942536](https://doi.org/10.1109/TAC.2019.2942536).

[17] B. K. Poolla, S. Bolognani, and F. Dörfler, “Optimal placement of virtual inertia in power grids,” *IEEE Transactions on Automatic Control*, vol. 62, no. 12, pp. 6209–6220, 2017, doi: [10.1109/TAC.2017.2703302](https://doi.org/10.1109/TAC.2017.2703302).

[18] J. Fu, A. Kumar, O. Nachum, G. Tucker, and S. Levine, “Diagnosing bottlenecks in deep Q-learning algorithms,” in *Proc. 36th Int. Conf. Machine Learning (ICML)*, PMLR 97:2021–2030, 2019.

[19] P. Henderson, R. Islam, P. Bachman, J. Pineau, D. Precup, and D. Meger, “Deep reinforcement learning that matters,” in *Proc. 32nd AAAI Conf. Artificial Intelligence (AAAI)*, 2018.

[20] S. Fujimoto, H. van Hoof, and D. Meger, “Addressing function approximation error in actor-critic methods,” in *Proc. 35th Int. Conf. Machine Learning (ICML)*, PMLR 80:1587–1596, 2018.

## Data and Reproducibility Statement

The trajectory records, formal analyses, and decision feeds used in this draft are retained in a hash-addressed local project archive. The manuscript reports only values bound to those registered artifacts. A public release and venue-specific reproducibility package have not yet been established and are not claimed here.

Generative AI tools assisted manuscript organization, prose drafting, and presentation checks for mathematical arguments, including a consultation on the modal structure of the cost definitions whose algebraic claims were verified analytically and numerically against the frozen definitions before use. The authors retain responsibility for final verification of the reported data, derivations, citations, and claims. No AI-generated experimental or simulation data are reported.
