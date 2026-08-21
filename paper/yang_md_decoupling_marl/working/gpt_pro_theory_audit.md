# GPT Pro theory audit request: bounded mathematics for the VSG manuscript

## Resolution status

This request has been answered and locally checked in
`paper/yang_md_decoupling_marl/working/theory_audit_bundle/`. Tasks A–E now have
conditional theorem statements, counterexamples, symbolic checks, and synthetic
certificate demonstrations. This file remains the provenance request, not an
open invitation to strengthen the manuscript claims.

The unresolved questions are project-specific: the actual ANDES DAE Jacobians
and algebraic conditioning, signed-amplitude trajectories with active-mode logs,
and an exact affine Youla/SLS map with an independently verified conic dual
certificate. The imported synthetic data are not VSG experiment evidence.

## Purpose

Audit and, where possible, repair the mathematical statements below for the manuscript titled exactly:

**Decoupling-Oriented Coordination of Paralleled  VSGs With Multi-Agent Reinforcement Learning**

The requested output is a theorem/lemma audit, not an invitation to invent experiment results. The empirical record already shows that one structured energy-port controller enters the prescribed development target region and passes a one-use unseen bank, so a universal impossibility theorem would contradict the data.

## Evidence boundary that must be preserved

### Main direct-M/D object

- Four VSG units; one independently executed action row per unit.
- Action (a_i=(a_i^M,a_i^D)\in[-1,1]^2), slew at most 0.25 per 0.2-s update.
- For either M or D,
  \[
  \Delta q(a)=\begin{cases}600a,&a\ge0,\\200a,&a<0,\end{cases}
  \]
  with physical lower bounds $M_i\ge20,D_i\ge10$.
- The strong deterministic law uses absolute values and other piecewise operations, so smoothness and odd symmetry cannot be assumed globally.
- Empirical result: the deterministic law improves two development endpoints by 60.79% and 64.13% versus zero action; a finite nine-law outcome-seeing oracle gives 0% further improvement on four evaluation profiles.
- Empirical result: three TD3/MATD3 arms over three seeds are 4.12/2.92, 4.16/3.13, and 5.09/3.30 times the deterministic cross/differential endpoints; all fail common/action guards.

### Auxiliary energy-port object

- Direct M/D commands are pinned to zero.
- A 0.4-Hz ring-edge bandpass produces normalized zero-sum commands, then a state-dependent feasible-headroom map produces physical power-like actions.
- On development, K=3.5 gives $(r_d,r_{cross})=(0.938947,0.539791)$.
- Frozen K=3.5 then passes an unseen bank at $(0.938218,0.793730)$, with all guards.
- Therefore, do not propose a theorem that all finite-order LTI controllers, all causal controllers, or all decoupling-oriented controllers are infeasible.

## Model A: ideal reduced electromechanical system

Assume

\[
\dot\theta=\omega,\qquad
M\dot\omega=-\omega_nL\theta-D\omega+w,
\]

where $L=L^\top\succeq0$, $L\mathbf1=0$, the graph is connected, and positive $M,D$ are diagonal. Define

\[
P_c=\frac14\mathbf1\mathbf1^\top,\qquad P_d=I-P_c,
\]

and

\[
G_{\omega w}(s)=s(s^2M+sD+\omega_nL)^{-1}.
\]

### Task A: exact-separation theorem

Check the following proposition:

> $P_dG_{\omega w}(s)P_c=P_cG_{\omega w}(s)P_d=0$ identically in s if and only if $M=mI$ and $D=dI$.

Please:

1. state the weakest sufficient assumptions on L, connectivity, input/output spaces, and the domain of s;
2. verify the high-frequency proof using the (s^{-1}M^{-1}) and (s^{-2}M^{-1}DM^{-1}) coefficients;
3. identify counterexamples if only one cross direction is required, if L is directed/unbalanced, or if the differential output is not full rank;
4. give manuscript-safe theorem and proof wording;
5. say explicitly why the theorem does not cover a nonlinear DAE, saturation, finite windows, or approximate thresholded decoupling.

## Model B: multiplicative parameter feedback

Assume locally

\[
\dot x=A(u)x+B_ww,\qquad u=\kappa(x),\qquad u_0=\kappa(0).
\]

### Task B: first-order authority lemma

Check the statement:

> If A and kappa are differentiable at the equilibrium, the closed-loop state Jacobian is $A(u_0)$; $D\kappa(0)$ does not appear because its contribution is multiplied by x.

Please:

1. provide the correct derivative proof and equilibrium conditions;
2. generalize, if valid, to $\dot x=f(x,u)$ under the condition $f(0,u)=0$ for all feasible u;
3. distinguish continuous-time state feedback from sampled-data zero-order-hold execution;
4. state what changes when the physical action is an additive power input;
5. give manuscript-safe wording that says “limited local first-order authority,” not “dynamic feedback cannot help.”

### Task C: nonsmooth signed-probe response

The actual decoder is piecewise asymmetric at zero and the deterministic law uses absolute values. Determine whether any useful replacement exists for the smooth expansion

\[
y_{odd}(\varepsilon)=\varepsilon y_1+\varepsilon^3y_3+\cdots.
\]

Please consider directional derivatives, Bouligand derivatives, Clarke generalized Jacobians, and hybrid switching. Answer:

1. Can the normalized signed-pair difference between two zero-bias controllers be $O(\varepsilon)$, $O(\varepsilon^2)$, or only $O(\varepsilon^3)$ in the actual nonsmooth setting?
2. What additional symmetry and smoothness assumptions would be required for a cubic-leading claim?
3. What finite-amplitude scaling experiment could distinguish these orders without assuming them?

Do not preserve the cubic-order claim unless it is rigorously justified.

## Task D: a legitimate bounded infeasibility certificate

We want to ask only whether a chosen local, finite-order, internally stabilizing controller class can enter

\[
\mathcal Q=\{r_d\le0.95,\ r_{cross}\le1.10\}
\]

over a finite scenario set and finite time horizon.

Give a rigorous formulation using Youla parameterization or system-level synthesis. Address:

1. the exact plant assumptions needed for a stable affine closed-loop response map;
2. how local/ring-edge information constraints can be imposed without destroying convexity;
3. how finite-window energy, action box, slew, and common-mode constraints can be represented or conservatively bounded;
4. how internal stability is certified;
5. what constitutes a real infeasibility certificate: solver status, primal/dual residuals, dual variables, Slater/strong-duality conditions, rational verification, and uncertainty robustness;
6. why generic SLSQP success or failure is not such a certificate;
7. how the state-dependent nonlinear feasible-headroom map affects convexity and what local or robust outer approximation is defensible.

## Task E: extension to a power-system DAE

For a semi-explicit index-1 DAE

\[
\dot x=f(x,y,u,w),\qquad 0=g(x,y,u,w),
\]

derive the reduced local Jacobian under valid (g_y^{-1}), and determine when the parameter-feedback lemma survives algebraic elimination. Identify failure modes caused by:

- action-dependent algebraic equations;
- singular or ill-conditioned (g_y);
- limiter/saturation mode changes;
- measurement filters and sampled controllers;
- a recovered coupling matrix that is only approximately symmetric and balanced.

## Required response format

For each task A–E, return:

1. **Verdict:** valid / valid with corrected assumptions / false;
2. **Minimal assumptions;**
3. **Proof or counterexample;**
4. **Exact manuscript-safe statement;**
5. **Forbidden stronger wording;**
6. **Additional matrices, trajectories, or implementation details needed for a stronger result.**

End with a compact table separating mathematically proved statements, empirically observed statements, plausible but unisolated mechanisms, and open questions.
