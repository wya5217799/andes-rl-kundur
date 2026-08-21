# Theory Audit and Repair for
# *Decoupling-Oriented Coordination of Paralleled VSGs With Multi-Agent Reinforcement Learning*

> **Purpose.** This document audits Tasks A–E in the supplied theory-audit request. It proves only statements supported by the stated models and assumptions. It does not invent experimental results, and it does not convert a bounded-class certificate into a universal impossibility theorem.

## Executive verdict

| Task | Verdict | Main correction |
|---|---|---|
| A. Exact common/differential separation | **Valid with corrected—and weaker—assumptions** | Connectivity and positive semidefiniteness of the Laplacian are unnecessary for the algebraic equivalence. Under the original symmetric balanced model, **either one full cross block alone** already forces homogeneous diagonal inertia and damping. |
| B. First-order authority of multiplicative parameter feedback | **Valid with corrected equilibrium and implementation assumptions** | The plant-state Jacobian is fixed by the equilibrium parameter bias, but this is only a local first-order statement. It does not rule out finite-amplitude, biased, additive-input, sampled/hybrid, or DAE-mediated authority. |
| C. Cubic signed-probe claim | **False for the stated nonsmooth implementation** | The asymmetric decoder and absolute-value operations invalidate a two-sided smooth odd-power expansion. For locally Lipschitz zero-bias multiplicative feedback, a controller-to-controller trajectory difference is generically only bounded as \(O(\varepsilon^2)\); its antisymmetric part may also be \(O(\varepsilon^2)\). |
| D. Bounded infeasibility certificate | **Valid with a precisely bounded convex controller class** | A legitimate statement requires a fixed LTI plant, an exact Youla/SLS class, convex finite-window constraints, and an independently verified conic dual certificate or lower bound. SLSQP failure is not a certificate. |
| E. DAE extension | **Valid with index-1 and regularity assumptions** | Algebraic elimination gives a Schur-complement Jacobian. Action dependence in the algebraic equations can create an additive first-order channel and invalidate the multiplicative-parameter lemma. |

The strongest manuscript-safe global conclusion is therefore:

> The ideal LTI model gives an exact structural characterization of common/differential separation, and zero-bias multiplicative parameter feedback has limited local first-order authority. Neither result proves that nonlinear, sampled, saturated, DAE, energy-port, or broader causal controller classes are infeasible. A genuine impossibility claim can only be made for an explicitly bounded controller class after a verifiable convex infeasibility certificate is obtained.

---

## 0. Scope and preserved evidence boundary

The supplied record distinguishes two control objects:

1. **Direct \(M/D\) object.** Four independently actuated VSG units use piecewise-asymmetric parameter increments, physical lower bounds, and a slew limit. A deterministic nonsmooth law materially improves two development endpoints, while the listed TD3/MATD3 arms perform substantially worse and fail guards.
2. **Auxiliary energy-port object.** Direct \(M/D\) commands are zero, while a ring-edge bandpass and state-dependent feasible-headroom map generate physical power-like actions. A frozen gain \(K=3.5\) enters the prescribed development region and passes an unseen bank with all guards.

Therefore:

- no theorem below says all finite-order LTI controllers are infeasible;
- no theorem says all causal or all decoupling-oriented controllers are infeasible;
- no theorem converts poor performance of the tested RL arms into a general learning-theoretic impossibility;
- no synthetic calculation in the accompanying code is an empirical VSG result.

---

# Task A — Exact common/differential separation

## A.1 Verdict

**Valid with corrected assumptions.**

For the original model with diagonal \(M,D\), symmetric \(L\), and \(L\mathbf 1=0\), the proposition is true. It can be strengthened:

- graph connectivity is not needed for the equivalence;
- \(L\succeq0\) is not needed for the algebraic separation claim;
- because the transfer matrix is symmetric under the original assumptions, either cross direction is already equivalent to the other;
- even without symmetry, either **full** one-sided cross identity forces \(M=mI\) and \(D=dI\); the appropriate right- or left-balance condition on \(L\) is then needed for sufficiency.

## A.2 Minimal assumptions

Let \(n\ge2\), and define

\[
P_c=\frac1n\mathbf1\mathbf1^\top,\qquad P_d=I-P_c.
\]

The weakest convenient assumptions for the two-sided theorem are:

1. \(M=\operatorname{diag}(m_1,\ldots,m_n)\) is nonsingular. Positivity \(m_i>0\) is physically appropriate but algebraically stronger than necessary.
2. \(D=\operatorname{diag}(d_1,\ldots,d_n)\). Positivity is again physical rather than required by the coefficient argument.
3. With \(K_L:=\omega_nL\), the coupling preserves the common/differential decomposition:
   \[
   [K_L,P_c]=0.
   \]
   A sufficient special case is \(L=L^\top\) and \(L\mathbf1=0\). More generally, for a directed matrix it is enough that
   \[
   L\mathbf1=\lambda\mathbf1,\qquad \mathbf1^\top L=\lambda\mathbf1^\top.
   \]
   For a balanced Laplacian, \(\lambda=0\).
4. The input and output spaces are the full complexifications of \(\mathbb R^n\), with common input \(P_cw\), full differential input \(P_dw\), common output \(P_c\omega\), and full differential output \(P_d\omega\). Hidden or rank-deficient input/output maps invalidate the scalar-homogeneity conclusion.
5. Define
   \[
   H(s)=s^2M+sD+K_L,\qquad G(s)=sH(s)^{-1}.
   \]
   The identity is interpreted as a **rational-matrix identity**: it holds on any nonempty open subset of the resolvent set \(\{s:\det H(s)\ne0\}\), equivalently wherever the rational continuation is defined. It is enough to assume it for all sufficiently large complex \(s\). A finite frequency grid or a single frequency is not enough.

Connectivity is useful for the physical interpretation \(\ker L=\operatorname{span}\{\mathbf1\}\), but it is not used in the exact-separation equivalence.

## A.3 Exact theorem

### Theorem A1 — two-sided exact separation

Assume items 1–5 above and \([K_L,P_c]=0\). Then the following are equivalent:

\[
P_dG(s)P_c\equiv0,\qquad P_cG(s)P_d\equiv0,
\]

and

\[
M=mI,\qquad D=dI
\]

for scalars \(m\ne0\) and \(d\). Under physical positivity, \(m>0\) and normally \(d>0\).

### Stronger one-sided refinement

Without assuming \([K_L,P_c]=0\), the exact one-sided statements are

\[
P_dG(s)P_c\equiv0
\quad\Longleftrightarrow\quad
\begin{cases}
M=mI,\\
D=dI,\\
K_L\mathbf1\in\operatorname{span}\{\mathbf1\},
\end{cases}
\]

and

\[
P_cG(s)P_d\equiv0
\quad\Longleftrightarrow\quad
\begin{cases}
M=mI,\\
D=dI,\\
\mathbf1^\top K_L\in\operatorname{span}\{\mathbf1^\top\}.
\end{cases}
\]

Hence, under the original symmetric-Laplacian assumptions, **either one cross identity alone is sufficient**. There is no one-sided counterexample unless another hypothesis is also weakened.

## A.4 Proof and verification of the high-frequency coefficients

Factor

\[
H(s)=s^2M\left(I+s^{-1}M^{-1}D+s^{-2}M^{-1}K_L\right).
\]

For sufficiently large \(|s|\), the Neumann expansion gives

\[
\begin{aligned}
G(s)
&=sH(s)^{-1}\\
&=s^{-1}M^{-1}
-s^{-2}M^{-1}DM^{-1}\\
&\quad+s^{-3}\left(M^{-1}DM^{-1}DM^{-1}-M^{-1}K_LM^{-1}\right)
+O(s^{-4}).
\end{aligned}
\]

The sign of the \(s^{-2}\) coefficient is negative.

Suppose first that

\[
P_dG(s)P_c\equiv0.
\]

Every Laurent coefficient of this rational identity must vanish. The \(s^{-1}\) coefficient gives

\[
P_dM^{-1}P_c=0.
\]

Since \(P_c=\mathbf1\mathbf1^\top/n\), this is equivalent to

\[
P_dM^{-1}\mathbf1=0,
\]

so \(M^{-1}\mathbf1=\alpha\mathbf1\). Because \(M\) is diagonal and nonsingular,

\[
\frac1{m_1}=\cdots=\frac1{m_n}=\alpha,
\]

and therefore \(M=mI\).

The \(s^{-2}\) coefficient then gives

\[
P_dM^{-1}DM^{-1}P_c=0.
\]

With \(M=mI\), this reduces to

\[
P_dD\mathbf1=0,
\]

which forces \(D=dI\) because \(D\) is diagonal.

The same argument applied to \(P_cG(s)P_d\equiv0\) uses the row conditions

\[
\mathbf1^\top M^{-1}P_d=0,
\qquad
\mathbf1^\top M^{-1}DM^{-1}P_d=0,
\]

and reaches the same conclusion.

To recover the coupling condition for the right-sided identity, note that

\[
P_dG(s)P_c=0
\]

implies \(H(s)^{-1}\mathbf1=\beta(s)\mathbf1\) for every resolvent point with \(s\ne0\). Since \(H(s)^{-1}\) is nonsingular, \(\beta(s)\ne0\), and therefore

\[
H(s)\mathbf1=\beta(s)^{-1}\mathbf1.
\]

After \(M=mI\) and \(D=dI\) are known,

\[
H(s)\mathbf1=(s^2m+sd)\mathbf1+K_L\mathbf1,
\]

so \(K_L\mathbf1\in\operatorname{span}\{\mathbf1\}\). The left-sided condition is analogous.

Conversely, if \(M=mI\), \(D=dI\), and \([K_L,P_c]=0\), then \(H(s)\) commutes with \(P_c\). At every resolvent point, so does \(H(s)^{-1}\), hence so does \(G(s)\). Therefore both cross blocks vanish.

## A.5 Counterexamples and boundary cases

### A.5.1 Only one cross direction under the original assumptions

There is **no counterexample**. When \(L=L^\top\), \(M=M^\top\), and \(D=D^\top\), the transfer matrix is complex symmetric:

\[
G(s)^\top=G(s).
\]

Thus

\[
\left(P_dG(s)P_c\right)^\top=P_cG(s)P_d.
\]

More strongly, the Laurent argument above shows that even without symmetry, either full one-sided rational identity forces homogeneous diagonal \(M,D\).

### A.5.2 Directed, row-balanced but not left-balanced coupling

Let

\[
L_{\rm dir}=
\begin{bmatrix}
1&-1&0&0\\
0&2&-2&0\\
0&0&3&-3\\
-4&0&0&4
\end{bmatrix}.
\]

This directed cycle is strongly connected and satisfies

\[
L_{\rm dir}\mathbf1=0,
\qquad
\mathbf1^\top L_{\rm dir}\ne0.
\]

With \(M=mI\) and \(D=dI\), common input remains common, so

\[
P_dG(s)P_c\equiv0.
\]

But differential input generally leaks into the common output, so

\[
P_cG(s)P_d\not\equiv0.
\]

The accompanying numerical check obtains a right-cross norm at machine precision and a nonzero left-cross norm. Thus symmetry can be weakened to balance/commutation, but not simply discarded.

### A.5.3 Rank-deficient differential output

Let

\[
C_d=\frac1{\sqrt2}[1,-1,0,0],
\]

and choose

\[
M=\operatorname{diag}(1,1,2,3),
\qquad
D=\operatorname{diag}(0.8,0.8,1.5,2.1),
\]

with the complete-graph Laplacian

\[
L=4I-\mathbf1\mathbf1^\top.
\]

The system is invariant under swapping units 1 and 2. A common input therefore produces equal responses at units 1 and 2, and

\[
C_dG(s)P_c\equiv0.
\]

Nevertheless, the full differential response is nonzero:

\[
P_dG(s)P_c\not\equiv0.
\]

A differential output of rank less than \(n-1\) can hide heterogeneous directions.

### A.5.4 A single frequency is insufficient

Set

\[
M=\operatorname{diag}(1,2,3,4),
\qquad
D=\operatorname{diag}(4,3,2,1),
\]

and let \(L\mathbf1=0\). At \(s=1\),

\[
(s^2M+sD)\mathbf1=(M+D)\mathbf1=5\mathbf1,
\]

so exact common/differential separation holds at that one frequency even though \(M,D\) are heterogeneous. At \(s=2\), it fails. A sampled frequency plot cannot prove a rational identity.

### A.5.5 Diagonality of \(M,D\) is essential

Let

\[
M=1.2P_c+2.3P_d,
\qquad
D=0.7P_c+1.9P_d,
\qquad
K_L=4P_d.
\]

All three matrices preserve the common/differential decomposition, so the transfer is exactly separated, but neither \(M\) nor \(D\) is a scalar multiple of \(I\). For general dense matrices, exact separation implies block invariance, not per-unit homogeneity.

## A.6 Manuscript-safe theorem and proof wording

> **Theorem (exact common/differential separation in the ideal LTI model).** Let \(P_c=\mathbf1\mathbf1^\top/n\) and \(P_d=I-P_c\). Assume \(M=\operatorname{diag}(m_i)\succ0\), \(D=\operatorname{diag}(d_i)\succ0\), and \(K_L=\omega_nL\) satisfies \([K_L,P_c]=0\); the latter holds, in particular, when \(L=L^\top\) and \(L\mathbf1=0\). Define \(G_{\omega w}(s)=s(s^2M+sD+K_L)^{-1}\) as a rational matrix. Then the common and differential subspaces are exactly decoupled,
> \[
> P_dG_{\omega w}(s)P_c=P_cG_{\omega w}(s)P_d=0,
> \]
> as rational identities if and only if \(M=mI\) and \(D=dI\). In fact, under the stated coupling assumption, either one of the two cross identities alone is sufficient.
>
> **Proof.** For large \(|s|\),
> \[
> G_{\omega w}(s)=s^{-1}M^{-1}-s^{-2}M^{-1}DM^{-1}+O(s^{-3}).
> \]
> If \(P_dG_{\omega w}P_c\equiv0\), the first coefficient gives \(P_dM^{-1}\mathbf1=0\), which forces all diagonal entries of \(M\) to be equal. The second coefficient then gives \(P_dD\mathbf1=0\), which forces all diagonal entries of \(D\) to be equal. The same conclusion follows from the opposite cross identity. Conversely, if \(M=mI\), \(D=dI\), and \([K_L,P_c]=0\), then \(s^2M+sD+K_L\), its inverse, and \(G_{\omega w}\) all commute with \(P_c\), so both cross blocks vanish. \(\square\)

## A.7 Forbidden stronger wording

Do not write any of the following:

- “Heterogeneous inertia or damping makes decoupling impossible for any controller.”
- “No causal controller can enter the target region.”
- “The theorem proves the nonlinear DAE is infeasible.”
- “Nonzero transfer cross-coupling prevents small finite-window cross energy.”
- “Approximate or thresholded decoupling is equivalent to the exact rational identity.”
- “A finite frequency sweep proves exact separation.”

## A.8 Why this theorem does not cover the implemented system

The theorem is restricted to an ideal, linear, time-invariant ODE with fixed matrices and full-state input/output channels. It does not cover:

- nonlinear network and converter equations;
- a semi-explicit DAE before valid algebraic elimination;
- saturation, physical lower bounds, or asymmetric decoding;
- slew limits and zero-order-hold execution;
- state-dependent headroom maps;
- finite time windows or endpoint ratios;
- thresholded approximate decoupling;
- nonlinear, hybrid, or time-varying controllers.

Exact nonzero cross transfer can coexist with small finite-window metrics, and exact zero cross transfer is stronger than entering a prescribed numerical target region.

## A.9 Additional information needed for a stronger result

1. The exact linearized \(M,D,L\) at every operating point and the state transformation used to recover them.
2. The actual disturbance-input and measured-output matrices; identity input/output cannot be presumed.
3. The exact common/differential projectors used by the metrics, including any mass-weighted or power-weighted definition.
4. A quantified symmetry/balance residual for the recovered coupling matrix.
5. Frequency-domain resolvent margins or time-domain induced-norm bounds for an approximate-separation theorem.
6. Exact finite-window metric definitions and denominators.

---

# Task B — First-order authority of multiplicative parameter feedback

## B.1 Verdict

**Valid with corrected equilibrium, regularity, and implementation assumptions.**

For

\[
\dot x=A(u)x+B_ww,
\qquad
u=\kappa(x),
\qquad
u_0=\kappa(0),
\]

the plant-state Jacobian at \((x,w)=(0,0)\) is \(A(u_0)\). The derivative \(D\kappa(0)\) does not enter because the parameter perturbation multiplies the zero equilibrium state.

This is a statement about the **local first-order plant-state linearization**. It is not a statement that dynamic feedback is useless.

## B.2 Minimal assumptions and equilibrium conditions

A minimal direct assumption is

\[
A(\kappa(x))\longrightarrow A(u_0)
\quad\text{as }x\to0.
\]

Thus differentiability of both \(A\) and \(\kappa\) is more than enough; continuity of the composition at zero suffices.

The equilibrium conditions are:

- \(w=0\);
- \(x=0\);
- \(u_0=\kappa(0)\) is feasible;
- there is no omitted affine term \(b(u)\) with \(b(u_0)\ne0\).

The given multiplicative model automatically satisfies

\[
A(u_0)0=0.
\]

If the physical equilibrium is \(x_e\ne0\), the coordinates must first be shifted. The conclusion survives only if the shifted reduced vector field vanishes at the shifted origin for all nearby feasible parameter values.

## B.3 Derivative proof

Define

\[
F(x)=A(\kappa(x))x.
\]

For any direction \(h\),

\[
\begin{aligned}
DF(0)h
&=\lim_{t\to0}\frac{A(\kappa(th))(th)-A(\kappa(0))0}{t}\\
&=\lim_{t\to0}A(\kappa(th))h\\
&=A(u_0)h.
\end{aligned}
\]

If \(A\) and \(\kappa\) are differentiable, the product-rule form is

\[
DF(0)h
=A(u_0)h+
DA(u_0)[D\kappa(0)h]\,0,
\]

and the second term vanishes.

For the full map

\[
F(x,w)=A(\kappa(x))x+B_ww,
\]

the first-order model is

\[
\delta\dot x=A(u_0)\delta x+B_w\delta w.
\]

## B.4 Generalization to \(\dot x=f(x,u)\)

Let

\[
F_{\rm cl}(x)=f(x,\kappa(x)).
\]

If \(f\) and \(\kappa\) are differentiable at \((0,u_0)\), then

\[
DF_{\rm cl}(0)
=f_x(0,u_0)+f_u(0,u_0)D\kappa(0).
\]

The parameter-feedback term disappears under the minimal condition

\[
f_u(0,u_0)D\kappa(0)=0.
\]

A convenient sufficient condition is

\[
f(0,\kappa(x))=0
\quad\text{for all sufficiently small }x.
\]

Indeed, differentiating the identically zero map \(x\mapsto f(0,\kappa(x))\) gives

\[
f_u(0,u_0)D\kappa(0)=0.
\]

The stronger statement

\[
f(0,u)=0
\quad\text{for every nearby feasible }u
\]

is also sufficient, provided \(\kappa(x)\) remains feasible. If the feasible set has a boundary or lower dimension, the required condition is only along tangent directions actually generated by \(D\kappa(0)\).

## B.5 Continuous-time state feedback versus sampled-data ZOH

Suppose the controller samples \(x_k\) every \(T_s\) seconds and holds

\[
u(t)=\kappa(x_k),\qquad t\in[kT_s,(k+1)T_s).
\]

For the multiplicative linear plant, the exact one-step map is

\[
x_{k+1}=\exp(A(\kappa(x_k))T_s)x_k.
\]

Because \(x=0\) is fixed for every held parameter value,

\[
D x_{k+1}\big|_{x_k=0}
=\exp(A(u_0)T_s).
\]

Thus \(D\kappa(0)\) still does not appear in the one-step plant-state Jacobian.

Important qualifications:

1. The sampled Jacobian is \(e^{A(u_0)T_s}\), not \(A(u_0)\).
2. Around a nonzero equilibrium or nonzero nominal trajectory, differentiation of the matrix exponential with respect to \(u\) generally contributes at first order.
3. Controller memory, filters, observers, or recurrent states must be included in an augmented sampled map. The plant block can remain unaffected while controller states and action outputs have first-order dynamics.
4. Delays, switching, saturation, and active-set changes can invalidate a single smooth Jacobian.

For a dynamic parameter controller with state \(z\), the local augmented Jacobian often has the triangular form

\[
\begin{bmatrix}
A(u_0)&0\\
Q_x&Q_z
\end{bmatrix},
\]

under the same zero-equilibrium multiplicative assumptions. The controller can have its own local dynamics, but there is no first-order path from \(z\) back into the plant state through a parameter perturbation multiplied by \(x=0\).

## B.6 Additive physical power input

If the physical action enters additively,

\[
\dot x=A_0x+B_pp+B_ww,
\qquad
p=\kappa(x),
\qquad
\kappa(0)=0,
\]

then

\[
D\dot x\big|_0=A_0+B_pD\kappa(0).
\]

The controller has direct local first-order authority.

For sampled-data ZOH,

\[
x_{k+1}=e^{A_0T_s}x_k+
\left(\int_0^{T_s}e^{A_0\tau}\,d\tau\right)B_p\kappa(x_k),
\]

so the sampled Jacobian is

\[
e^{A_0T_s}+\Gamma(T_s)B_pD\kappa(0).
\]

This distinction is central: the auxiliary energy-port controller is not covered by a lemma derived for multiplicative \(M/D\) parameter feedback.

## B.7 Manuscript-safe wording

> **Lemma (limited local first-order authority of zero-bias multiplicative parameter feedback).** Consider \(\dot x=A(u)x+B_ww\) with static state feedback \(u=\kappa(x)\), and let \(u_0=\kappa(0)\). If \(A\circ\kappa\) is continuous at the equilibrium, then the closed-loop plant-state vector field is differentiable at \(x=0\) with Jacobian \(A(u_0)\). Consequently, differentiable policies that share the same equilibrium parameter bias \(u_0\) share the same local first-order plant-state linearization. This statement concerns only zero-state, multiplicative parameter actuation; it does not exclude changes due to a different bias, finite-amplitude nonlinear effects, sampled or hybrid execution, controller internal states, algebraic-network mediation, or additive power actuation.

A general nonlinear version is:

> **Corollary.** For \(\dot x=f(x,u)\), \(u=\kappa(x)\), the closed-loop Jacobian is \(f_x(0,u_0)+f_u(0,u_0)D\kappa(0)\). If \(f(0,\kappa(x))\equiv0\) locally, then \(f_u(0,u_0)D\kappa(0)=0\), and the Jacobian reduces to \(f_x(0,u_0)\).

## B.8 Forbidden stronger wording

Do not write:

- “Dynamic feedback cannot help.”
- “The policy has no control authority.”
- “All zero-bias controllers have identical trajectories.”
- “The controller cannot change transient energy.”
- “The result applies unchanged to additive power injection.”
- “The result applies unchanged after DAE elimination.”
- “The result applies around any nonzero operating trajectory.”

## B.9 Additional information needed for a stronger result

1. The exact equilibrium and coordinate shift.
2. Whether the action changes only coefficients multiplying the incremental state or also changes affine injections/equilibria.
3. Controller bias \(u_0\), controller internal states, filters, delays, and sample period.
4. The ZOH/FOH implementation and whether the action changes within the 0.2-s interval.
5. Active limiter/saturation modes at the nominal point.
6. The reduced DAE input Jacobian from Task E.

---

# Task C — Nonsmooth signed-probe response

## C.1 Verdict

**False as a general claim for the implemented decoder and deterministic law.**

The expansion

\[
y_{\rm odd}(\varepsilon)
=\varepsilon y_1+\varepsilon^3y_3+\cdots
\]

requires a two-sided smooth dependence on the signed amplitude. The actual decoder is continuous and piecewise linear but not differentiable at zero, and the deterministic law contains absolute values and other branch operations. A cubic-leading claim cannot be retained without additional assumptions and direct order verification.

## C.2 First clarify the quantity and normalization

For controllers \(j=1,2\), let \(Y_j(\varepsilon)\) denote a trajectory or scalar output under the signed exogenous profile

\[
w_\varepsilon=\varepsilon\bar w,
\qquad \varepsilon\in\mathbb R.
\]

Define the controller difference

\[
\delta(\varepsilon)=Y_1(\varepsilon)-Y_2(\varepsilon)
\]

and its antisymmetric signed-pair component

\[
\delta_{\rm odd}(\varepsilon)
=\frac{\delta(+\varepsilon)-\delta(-\varepsilon)}2,
\qquad \varepsilon>0.
\]

All order statements below refer to this **raw** quantity or to normalization by a fixed nonzero scale. If the reported quantity is divided by \(\varepsilon^q\), the apparent order decreases by \(q\). If it is divided by a baseline energy that itself scales as \(O(\varepsilon^2)\), an \(O(\varepsilon^2)\) numerator may appear as \(O(1)\). Therefore no “normalized” order is meaningful until the denominator is specified.

## C.3 Directional derivatives of the actual decoder

For one scalar component,

\[
h(a)=
\begin{cases}
600a,&a\ge0,\\
200a,&a<0.
\end{cases}
\]

The Bouligand/Hadamard directional derivative at zero is

\[
h'(0;v)=
\begin{cases}
600v,&v\ge0,\\
200v,&v<0.
\end{cases}
\]

This derivative is positively homogeneous but not linear. The Clarke generalized Jacobian is

\[
\partial_C h(0)=[200,600].
\]

For the componentwise vector decoder,

\[
\partial_C h(0)
=\{\operatorname{diag}(\gamma_i):\gamma_i\in[200,600]\}.
\]

The signed decoder pair itself has

\[
\frac{h(+\varepsilon)-h(-\varepsilon)}2=400\varepsilon,
\]

and an even contamination

\[
\frac{h(+\varepsilon)+h(-\varepsilon)}2=200\varepsilon.
\]

Thus both odd and even signed components occur at first order in the decoded physical parameter increment.

For \(|x|\),

\[
(|\cdot|)'(0;v)=|v|,
\qquad
\partial_C|\cdot|(0)=[-1,1].
\]

The Clarke set is useful for bounds, but it does not select the actual sign-dependent branch and does not by itself establish a power-law order. The Bouligand directional map is more informative for paired signed probes.

## C.4 What orders are possible?

### C.4.1 Decoder or action response

The raw decoder response is generically

\[
O(\varepsilon).
\]

This does not yet imply an \(O(\varepsilon)\) difference in the plant trajectory when the action enters only multiplicatively.

### C.4.2 Two zero-bias locally Lipschitz multiplicative controllers

Assume both controllers have the same equilibrium bias \(u_0\), the same equilibrium initial condition \(x_j(0)=0\) (or a common initial perturbation of order \(O(\varepsilon)\)), and the same first-order plant map. Assume also that the plant coefficient map is locally Lipschitz in the parameter, each policy is locally Lipschitz with \(\kappa_j(0)=u_0\), and both signed trajectories remain in one common active-mode region on a fixed finite horizon. The closed loops can then be written as

\[
\dot x_j=A_0x_j+B_w\varepsilon\bar w+R_j(x_j),
\]

with

\[
\|R_j(x)\|\le c\|x\|^2
\]

near zero. This quadratic remainder follows because \(\kappa_j(x)-u_0=O(\|x\|)\), the coefficient perturbation is \(O(\|x\|)\), and it multiplies \(x\).

By a finite-horizon Grönwall estimate,

\[
\|x_j\|_{[0,T]}=O(\varepsilon).
\]

For \(e=x_1-x_2\),

\[
\dot e=A_0e+R_1(x_1)-R_2(x_2),
\]

and the forcing term is \(O(\varepsilon^2)\). Hence

\[
\|x_1-x_2\|_{[0,T]}=O(\varepsilon^2).
\]

Therefore, under these assumptions, an \(O(\varepsilon)\) controller-to-controller plant-state difference is excluded, but only because both controllers share the same first-order plant map and remain locally Lipschitz in a common mode.

### C.4.3 Why the antisymmetric difference may be \(O(\varepsilon^2)\)

In a nonsmooth system, separate one-sided expansions can have different quadratic coefficients:

\[
\delta(+\varepsilon)=c_+\varepsilon^2+o(\varepsilon^2),
\qquad
\delta(-\varepsilon)=c_-\varepsilon^2+o(\varepsilon^2).
\]

Then

\[
\delta_{\rm odd}(\varepsilon)
=\frac{c_+-c_-}{2}\varepsilon^2+o(\varepsilon^2).
\]

The asymmetric decoder and absolute-value terms provide exactly the kind of branch dependence that can make \(c_+\ne c_-\). Thus \(O(\varepsilon^2)\), not \(O(\varepsilon^3)\), is the generic manuscript-safe order for the antisymmetric controller difference under locally Lipschitz multiplicative feedback.

### C.4.4 When \(O(\varepsilon)\) can occur

An \(O(\varepsilon)\) controller-to-controller trajectory difference can occur if any first-order-equivalence assumption fails, for example:

- a relay, sign law, or mode selector has an \(O(1)\) jump at zero;
- the two controllers have different equilibrium biases;
- the physical action enters additively;
- the nominal point lies on a limiter or guard and the two signs select different first-order modes;
- the output functional or normalization divides by \(\varepsilon\);
- a nontransverse or grazing hybrid event destroys a bounded smooth sensitivity.

### C.4.5 When \(O(\varepsilon^3)\) is justified

Suppose \(\delta(\varepsilon)\) is \(C^3\) as a two-sided function of signed \(\varepsilon\), \(\delta(0)=0\), and the two controllers share the same first derivative, so \(\delta'(0)=0\). Then

\[
\delta(\varepsilon)
=\frac12\delta''(0)\varepsilon^2
+\frac16\delta'''(0)\varepsilon^3
+o(\varepsilon^3),
\]

so

\[
\delta_{\rm odd}(\varepsilon)
=\frac16\delta'''(0)\varepsilon^3+o(\varepsilon^3).
\]

This establishes \(O(\varepsilon^3)\), but a **cubic-leading** term additionally requires \(\delta'''(0)\ne0\).

## C.5 Additional assumptions required for a cubic-leading claim

At minimum:

1. Each controller’s closed-loop signed-amplitude map is \(C^3\) on a two-sided neighborhood of zero over the full evaluation horizon.
2. Both controllers use the same equilibrium, parameter bias, initial state, and exactly opposite exogenous profiles \(\pm\varepsilon\bar w\).
3. Their first-order plant-output derivatives agree.
4. No decoder kink, absolute-value kink, saturation boundary, slew corner, headroom boundary, guard, reset, or active-set change is encountered near zero.
5. The output functional is \(C^3\); max, absolute value, threshold indicators, RMS at a zero signal, and ratios with vanishing denominators require separate treatment.
6. The normalizer tends to a nonzero constant.
7. For the actual decoder, either the positive and negative slopes must be equal, the first-order controller command must vanish so the kink is not seen at the relevant order, or an explicit directional calculation must prove \(c_+=c_-\).

Global odd symmetry is sufficient but stronger than necessary. The essential requirement is equality of the two one-sided quadratic coefficients.

## C.6 Hybrid switching

If both signs follow the same sequence of smooth modes and all guard crossings are transverse, trajectory sensitivities can be propagated with mode Jacobians and saltation matrices. Separate \(+\) and \(-\) directional derivatives should still be computed.

If the nominal trajectory grazes a guard, has simultaneous events, chatters, changes limiter mode, or lies exactly at a reset discontinuity, a polynomial expansion may not exist. In that case, only finite-amplitude bounds and empirical scaling are defensible.

## C.7 Finite-amplitude scaling experiment

Use raw deterministic trajectories before non-smooth endpoint normalization wherever possible.

### Experiment design

1. Choose a geometric amplitude ladder, for example
   \[
   \varepsilon_k=\varepsilon_0 2^{-k},\qquad k=0,\ldots,K,
   \]
   with at least 5–7 usable scales above the numerical/noise floor.
2. For each controller \(j\), amplitude \(\varepsilon_k\), and sign \(\sigma\in\{+1,-1\}\), run the identical scenario with
   \[
   w=\sigma\varepsilon_k\bar w.
   \]
3. Record full trajectories, decoded actions, active limiter/saturation flags, headroom states, guard events, and mode sequences.
4. Form
   \[
   \delta_+(\varepsilon_k)=Y_1(+\varepsilon_k)-Y_2(+\varepsilon_k),
   \]
   \[
   \delta_-(\varepsilon_k)=Y_1(-\varepsilon_k)-Y_2(-\varepsilon_k),
   \]
   \[
   \delta_{\rm odd}(\varepsilon_k)=\frac{\delta_+-\delta_-}{2},
   \qquad
   \delta_{\rm even}(\varepsilon_k)=\frac{\delta_++\delta_-}{2}.
   \]
5. Use a fixed trajectory norm, such as a weighted \(L_2\) norm or a fixed linear endpoint map. Do not change the normalizer across amplitudes.
6. Estimate the local order by
   \[
   \widehat p_k=
   \frac{\log\|\delta_{\rm odd}(\varepsilon_k)\|-
   \log\|\delta_{\rm odd}(\varepsilon_{k+1})\|}
   {\log\varepsilon_k-
   \log\varepsilon_{k+1}}.
   \]
   A robust log-log regression over consecutive scales is preferable to one ratio.
7. Check the compensated quantities
   \[
   \frac{\|\delta_{\rm odd}\|}{\varepsilon},
   \qquad
   \frac{\|\delta_{\rm odd}\|}{\varepsilon^2},
   \qquad
   \frac{\|\delta_{\rm odd}\|}{\varepsilon^3}.
   \]
   A stable nonzero plateau identifies the corresponding order.
8. Reject a fitted order if mode signatures differ across the fitted amplitude range or if the signal is within the integration/noise floor.

For stochastic policies, freeze evaluation noise or use common random numbers and confidence intervals. Training-seed variability is not a substitute for repeated signed probes at a fixed controller.

## C.8 Manuscript-safe wording

> **Nonsmooth signed-probe statement.** The implemented action decoder is directionally differentiable but not differentiable at zero, with positive and negative directional gains 600 and 200, respectively; the deterministic law also contains absolute-value and piecewise operations. Therefore a two-sided smooth odd-power expansion cannot be assumed. For two locally Lipschitz controllers that share the same equilibrium bias, equilibrium initial condition (or common \(O(\varepsilon)\) initial perturbation), first-order plant map, and active-mode sequence, and whose actions enter only through multiplicative parameter variation, the controller-to-controller plant-state difference is \(O(\varepsilon^2)\) over a fixed horizon. Their antisymmetric signed-pair difference may also be \(O(\varepsilon^2)\) because the two one-sided quadratic coefficients need not agree. A cubic-leading term requires an independently justified \(C^3\) signed-amplitude map, matched first derivatives, equal one-sided quadratic coefficients, and no active-set changes.

## C.9 Forbidden stronger wording

Do not write:

- “The signed-pair controller difference is necessarily cubic.”
- “Odd symmetry follows from zero bias.”
- “The asymmetric decoder can be replaced by a single derivative at zero.”
- “A Clarke generalized Jacobian proves a unique Taylor coefficient.”
- “Hybrid switching preserves the smooth expansion.”
- “An observed slope near three at two amplitudes proves cubic asymptotics.”

## C.10 Additional information needed for a stronger result

1. Exact definitions of \(Y_j\), \(y_{\rm odd}\), and the normalizer.
2. Raw \(+\varepsilon\) and \(-\varepsilon\) trajectories, not only ratios.
3. Controller action formulas and the sign of every decoder input near zero.
4. Active-set, saturation, slew, limiter, and headroom logs.
5. Event times and guard transversality data for hybrid modes.
6. Numerical integration tolerances and a measured noise floor.
7. At least 5–7 geometric amplitudes within a common mode region.

---

# Task D — A legitimate bounded infeasibility certificate

## D.1 Verdict

**Valid with corrected assumptions and a strictly bounded claim.**

A rigorous certificate can establish only:

> No controller in the explicitly defined local, finite-order, internally stabilizing LTI class satisfies the specified finite-scenario, finite-window performance and guard constraints for the specified plant model and uncertainty set.

It cannot establish infeasibility of all causal controllers, all nonlinear controllers, all DAE controllers, or the already observed energy-port implementation.

## D.2 Exact plant assumptions for an affine closed-loop response map

A convenient discrete-time formulation is appropriate for the 0.2-s sampled execution. Assume:

1. A fixed, finite-dimensional, proper real-rational LTI generalized plant
   \[
   \begin{bmatrix}z\\y\end{bmatrix}
   =P(z)\begin{bmatrix}w\\u\end{bmatrix},
   \qquad
   P=\begin{bmatrix}P_{11}&P_{12}\\P_{21}&P_{22}\end{bmatrix},
   \]
   with a well-posed feedback interconnection.
2. A stabilizable/detectable realization of \(P_{22}\), sufficient for a doubly coprime factorization and Youla parameterization.
3. The finite scenarios differ only in exogenous trajectories, initial conditions, or fixed affine offsets. They use the same plant and the same controller. If the plant matrices vary by scenario, exact common-controller synthesis is generally no longer the same convex problem and may become nonconvex.
4. The controller class is finite-dimensional by construction, for example
   \[
   Q(z;q)=\sum_{k=0}^{N_Q}Q_kz^{-k}
   \]
   or a fixed stable basis with finite coefficient vector \(q\). FIR \(Q\) is stable automatically.
5. Every finite-window metric and guard is a convex function of an affine closed-loop trajectory. Denominators in performance ratios are fixed positive constants.

Under a doubly coprime factorization, all internally stabilizing controllers are parameterized by stable \(Q\), and the relevant closed-loop map has the affine form

\[
T_{zw}(Q)=T_{11}+T_{12}QT_{21}.
\]

For a fixed stable finite basis and a fixed scenario \(w^{(\ell)}\), every stacked trajectory is affine in \(q\):

\[
z^{(\ell)}=a_z^{(\ell)}+F_z^{(\ell)}q,
\qquad
u^{(\ell)}=a_u^{(\ell)}+F_u^{(\ell)}q.
\]

This is the cleanest route to a finite-dimensional convex certificate.

## D.3 SLS alternative

For the discrete-time state-feedback plant

\[
x_{t+1}=Ax_t+Bu_t+\delta_t,
\]

the stable closed-loop responses \((\Phi_x,\Phi_u)\) satisfy

\[
\begin{bmatrix}zI-A&-B\end{bmatrix}
\begin{bmatrix}\Phi_x\\\Phi_u\end{bmatrix}=I,
\qquad
\Phi_x,\Phi_u\in z^{-1}\mathcal{RH}_\infty.
\]

Then

\[
K=\Phi_u\Phi_x^{-1}
\]

has an internally stabilizing SLS realization. For exact FIR responses

\[
\Phi_x=\sum_{k=1}^N X_kz^{-k},
\qquad
\Phi_u=\sum_{k=1}^N U_kz^{-k},
\]

the affine achievability equations are

\[
X_1=I,
\]

\[
X_{k+1}=AX_k+BU_k,
\qquad k=1,\ldots,N-1,
\]

\[
AX_N+BU_N=0.
\]

If the exact terminal condition is omitted, a finite truncation by itself does **not** certify infinite-horizon internal stability. A stable tail or robust residual condition is required.

For dynamic output feedback, use the full output-feedback SLS response parameterization or Youla. A state-feedback SLS certificate cannot silently be reinterpreted as a local-output controller certificate.

## D.4 Local and ring-edge information constraints

### Youla route

Let \(\mathcal S\) be the desired causal sparsity/delay subspace for \(K\). A convex constraint on the Youla parameter enforces the controller structure exactly only when \(\mathcal S\) is quadratically invariant with respect to \(P_{22}\):

\[
K P_{22} K\in\mathcal S
\quad\text{for every }K\in\mathcal S.
\]

Under quadratic invariance, locality, sparsity, and communication delays can be imposed as linear constraints on the appropriate Youla coordinates.

Without quadratic invariance, simply zeroing entries of \(Q\) does not generally impose the desired zeros in \(K\).

### SLS route

Locality and delay constraints can be placed directly on impulse-response blocks:

\[
(X_k)_{ij}=0,
\qquad
(U_k)_{ij}=0
\]

whenever subsystem \(j\) lies outside the permitted \(k\)-step information neighborhood of subsystem \(i\). These are linear equality constraints and therefore preserve convexity. They certify locality of the specified SLS implementation, not every possible realization of an algebraically equivalent controller.

For a ring-edge architecture, specify:

- permitted neighboring measurements;
- sensing and communication delays;
- whether edge states may be shared;
- whether a zero-sum/common-mode constraint is imposed on controller output or only after the physical headroom map.

## D.5 Convex representation of finite-window objectives and guards

Let \(q\) collect the finite controller parameters. For scenario \(\ell\), write

\[
y_d^{(\ell)}=a_d^{(\ell)}+F_d^{(\ell)}q,
\]

\[
y_{\rm cross}^{(\ell)}=a_c^{(\ell)}+F_c^{(\ell)}q,
\]

\[
u^{(\ell)}=a_u^{(\ell)}+F_u^{(\ell)}q.
\]

Assume fixed positive reference scales \(e_{d,\ell}\) and \(e_{c,\ell}\). If

\[
r_d^{(\ell)}=\frac{\|W_dy_d^{(\ell)}\|_2}{e_{d,\ell}},
\qquad
r_{\rm cross}^{(\ell)}=\frac{\|W_cy_{\rm cross}^{(\ell)}\|_2}{e_{c,\ell}},
\]

then the target constraints are second-order-cone constraints:

\[
\|W_dy_d^{(\ell)}\|_2
\le0.95e_{d,\ell},
\]

\[
\|W_cy_{\rm cross}^{(\ell)}\|_2
\le1.10e_{c,\ell}.
\]

A useful margin problem is

\[
\begin{aligned}
\min_{q,t}\quad&t\\
\text{s.t.}\quad
&\|W_dy_d^{(\ell)}\|_2
\le t(0.95)e_{d,\ell},\\
&\|W_cy_{\rm cross}^{(\ell)}\|_2
\le t(1.10)e_{c,\ell},\\
&\text{all action, slew, structure, and stability constraints},\\
&t\ge0,
\end{aligned}
\]

for every scenario \(\ell\). A rigorously verified lower bound \(t_\star>1\) proves that the bounded class cannot enter \(\mathcal Q\).

### Action box

If the optimized variable is the actual physical action and its trajectory is affine in \(q\),

\[
-u_{\max}\le a_u^{(\ell)}+F_u^{(\ell)}q\le u_{\max}
\]

is linear.

Physical lower bounds such as \(M_i\ge20\), \(D_i\ge10\) are also affine if the physical parameter increments are affine decision outputs. The asymmetric normalized decoder can make the exact normalized-action relation piecewise; choosing physical increments as synthesis outputs or using a certified convex outer relaxation avoids an unacknowledged disjunction.

### Slew

Let \(D_T\) be the first-difference matrix. Then

\[
-\Delta u_{\max}\le
D_T(a_u^{(\ell)}+F_u^{(\ell)}q)
\le\Delta u_{\max}
\]

is linear.

The exact normalized slew constraint under a piecewise asymmetric decoder is not automatically equivalent to a symmetric physical slew box. Its graph must be modeled exactly or outer-relaxed.

### Common mode

Exact zero common mode is

\[
P_cu_t^{(\ell)}=0.
\]

A bounded common-mode guard such as

\[
\|P_cu_t^{(\ell)}\|_\infty\le\gamma_c
\]

is linear after standard epigraph expansion. A finite-window common energy

\[
\|W_cP_cu^{(\ell)}\|_2\le\gamma_c
\]

is second-order-cone representable.

### Energy and endpoint details

A quadratic form \(y^THy\) is convex only if \(H\succeq0\). Factor \(H=R^TR\) and impose a norm bound. Indefinite cross-products, controller-dependent denominators, ratios of two variable energies, or differences of convex terms are not directly convex. They require an exact reformulation or a conservative bound.

The actual definitions of \(r_d\) and \(r_{\rm cross}\) were not supplied in the request, so the SOC representation above is conditional on fixed-denominator norm or positive-semidefinite energy definitions.

## D.6 Internal stability certification

### Youla

Internal stability is guaranteed when:

1. the generalized plant admits the stated doubly coprime factorization;
2. \(Q\in\mathcal{RH}_\infty\) is proper and stable;
3. the interconnection is well posed;
4. the controller is reconstructed with the same factorization and no unverified implementation substitution.

An FIR or fixed stable-basis \(Q\) gives a finite-order controller, with order bounded by the factorization realization plus the chosen basis order.

### SLS

Internal stability is guaranteed by stable response matrices satisfying the exact SLS affine constraints and by an internally stable SLS realization. A truncated finite-horizon trajectory optimization without a stable infinite-horizon extension is insufficient.

### Direct state-space coefficient optimization

Optimizing controller numerator/denominator coefficients directly normally produces nonconvex stability constraints. A local optimizer over those coefficients does not inherit the Youla/SLS guarantee.

## D.7 What constitutes a real infeasibility certificate

Consider the conic feasibility form

\[
Ax=b,
\qquad
Gx+s=h,
\qquad
s\in\mathcal K.
\]

A Farkas certificate is a pair \((y,z)\) satisfying

\[
A^Ty+G^Tz=0,
\qquad
z\in\mathcal K^*,
\]

and

\[
b^Ty+h^Tz<0.
\]

If a primal feasible point existed, then

\[
b^Ty+h^Tz=s^Tz\ge0,
\]

which is a contradiction.

For the margin formulation, a dual feasible point with a verified objective lower bound \(t_L>1\) is often numerically more useful than an “infeasible” status at the hard threshold \(t\le1\).

A manuscript-grade certificate should report:

1. **Exact problem definition:** plant version, sampling, controller order/basis, information pattern, scenarios, horizon, metrics, and all guards.
2. **Solver status:** primal infeasible, dual certificate found, or optimal margin.
3. **Primal residuals:** equality, cone, and bound violations.
4. **Dual residuals:** stationarity and dual-cone membership.
5. **Duality gap or separation margin:** not merely a status string.
6. **Dual variables/ray:** saved in machine-readable form.
7. **Scaling and conditioning:** badly scaled, nearly feasible problems can generate unreliable status reports.
8. **Strong-duality conditions:** Slater regularity for the margin problem, or an independently checked Farkas ray for direct infeasibility. A valid Farkas ray is a proof even without invoking Slater; Slater helps guarantee dual attainment and zero gap.
9. **Independent verification:** recompute residuals outside the modeling layer, preferably at higher precision.
10. **Rational or interval verification:** for rational LP data, reconstruct rational multipliers; for SOCP/SDP, use interval bounds on stationarity, cone membership, eigenvalues, and the negative separation margin.
11. **Uncertainty robustness:** prove the certificate over the declared uncertainty set, or show that the separation margin exceeds the worst-case effect of data perturbations.

A nominal certificate covers only its finite plant/scenario set. It does not automatically cover the unseen bank.

## D.8 Why generic SLSQP success or failure is not a certificate

SLSQP is a local nonlinear constrained optimizer.

- **Failure** may mean poor initialization, ill conditioning, inaccurate derivatives, a bad penalty path, or convergence to a nonstationary point. It does not prove global infeasibility.
- **Success** provides at most a candidate local solution. A candidate that independently satisfies every constraint is a feasibility witness for that candidate, but the status does not certify global optimality, internal stability, or correctness of the plant/controller parameterization.
- Repeated failures from multiple starts still do not produce a Farkas separator.

The acronym SLSQP should not be confused with System Level Synthesis.

## D.9 State-dependent nonlinear feasible-headroom map

Let the physical action be

\[
p_t=H(x_t)v_t,
\]

where \(v_t\) is a normalized zero-sum command and \(H(x_t)\) encodes positive/negative feasible headroom. This creates state-action products and branch dependence. The exact closed-loop map is generally no longer affine in \(q\), and the synthesis problem is generally nonconvex.

Defensible alternatives are:

### D.9.1 Frozen nominal map

Use

\[
p_t\approx H(\bar x_t)v_t.
\]

This is only a local design approximation. It is not an infeasibility certificate unless a trust region and a certified remainder bound are included.

### D.9.2 Robust additive-error model

If \(H\) is Lipschitz on a certified state tube \(\|x_t-\bar x_t\|\le\rho_t\), write

\[
p_t=H(\bar x_t)v_t+e_t,
\]

with

\[
\|e_t\|\le L_H\rho_t\|v_t\|.
\]

Treat \(e_t\) as an adversarial bounded uncertainty and robustify all performance/guard constraints.

### D.9.3 Convex-hull/McCormick outer relaxation

For bounded scalar factors, introduce lifted variables for \(h_tv_t\) and impose McCormick envelopes. This gives a convex **outer** approximation of the nonlinear graph.

If the outer relaxation is infeasible, the original nonlinear class is infeasible. If the outer relaxation is feasible, the original problem may still be infeasible.

### D.9.4 Authority-enlarging outer bound

Allow any physical action in a global headroom box, perhaps with only the zero-sum and slew constraints retained. This enlarges the true actuator set. Infeasibility of this larger set is a valid but potentially conservative impossibility certificate.

An inner approximation has the opposite logic: it can certify a feasible controller after direct validation, but its infeasibility says nothing about the original class.

## D.10 Manuscript-safe bounded-certificate statement

> **Proposition (bounded controller-class infeasibility certificate).** Fix a sampled LTI generalized plant, a finite scenario set and horizon, fixed positive performance normalizers, and a finite-dimensional internally stabilizing controller class represented by a stable Youla parameter or exact SLS responses. Assume the locality/delay constraints are imposed by a convexity-preserving Youla/QI or SLS formulation, and assume all finite-window performance and guard constraints are conic representable in the affine closed-loop responses. Let \(t_\star\) be the optimum of the target-scaling conic program. If an independently verified dual feasible point gives a lower bound \(t_L>1\) on \(t_\star\), then no controller in this specified class reaches \(\mathcal Q=\{r_d\le0.95,r_{\rm cross}\le1.10\}\) on the specified scenarios and horizon. The same conclusion follows from an independently verified conic Farkas certificate for the hard target constraints. The result makes no claim about controllers outside the class, nonlinear state-dependent headroom maps outside the certified relaxation, different plants, or unseen scenarios.

## D.11 Forbidden stronger wording

Do not write:

- “The target is fundamentally impossible.”
- “All finite-order LTI controllers are infeasible,” unless the parameterization truly includes all such controllers of the declared order and structure.
- “All local controllers are infeasible,” without a complete and convexly represented local class.
- “Solver failure proves infeasibility.”
- “A nominal certificate covers plant uncertainty or unseen scenarios.”
- “An infeasible inner approximation proves the nonlinear headroom controller is infeasible.”
- “A feasible outer relaxation proves the original nonlinear controller is feasible.”

## D.12 Additional information needed to compute the actual certificate

1. Exact sampled or continuous generalized plant matrices and sampling method.
2. Measured-output and action-input definitions.
3. Controller order, stable basis/FIR horizon, ring information pattern, and delays.
4. Exact formulas for \(r_d\), \(r_{\rm cross}\), their denominators, and aggregation across scenarios.
5. Every action, physical lower-bound, slew, common-mode, and guard constraint.
6. All finite scenario trajectories and initial conditions.
7. Exact feasible-headroom map and certified state/headroom bounds.
8. Plant/model uncertainty sets and numerical tolerances.
9. Solver conic data and exported primal/dual solutions.

---

# Task E — Extension to a power-system DAE

## E.1 Verdict

**Valid with index-1, smoothness, and equilibrium assumptions.**

The local DAE can be reduced by the implicit function theorem only when the algebraic Jacobian is nonsingular. After reduction, the multiplicative-parameter lemma survives only if the reduced vector field has no additive first-order action channel along the controller’s feasible directions.

## E.2 Equilibrium and index-1 assumptions

Let

\[
\dot x=f(x,y,u,w),
\qquad
0=g(x,y,u,w),
\]

and let \((x_0,y_0,u_0,w_0)\) satisfy

\[
f(x_0,y_0,u_0,w_0)=0,
\qquad
g(x_0,y_0,u_0,w_0)=0.
\]

Assume:

1. \(f,g\) are \(C^1\) near the equilibrium; \(C^2\) is preferable for remainder bounds.
2. The algebraic equation is square in \(y\).
3. \(g_y(x_0,y_0,u_0,w_0)\) is nonsingular and remains nonsingular in the local neighborhood.
4. The controller is differentiable in the relevant mode and maps nearby states to feasible actions.

Then the implicit function theorem gives

\[
y=h(x,u,w)
\]

locally.

## E.3 Reduced local Jacobian

Differentiating \(g(x,h(x,u,w),u,w)=0\) gives

\[
h_x=-g_y^{-1}g_x,
\qquad
h_u=-g_y^{-1}g_u,
\qquad
h_w=-g_y^{-1}g_w.
\]

Define the reduced ODE vector field

\[
F(x,u,w)=f(x,h(x,u,w),u,w).
\]

Its local Jacobians are

\[
A_r=F_x=f_x-f_yg_y^{-1}g_x,
\]

\[
B_{u,r}=F_u=f_u-f_yg_y^{-1}g_u,
\]

\[
B_{w,r}=F_w=f_w-f_yg_y^{-1}g_w.
\]

All derivatives are evaluated at the equilibrium.

With static feedback

\[
u-u_0=K(x-x_0)+o(\|x-x_0\|),
\qquad
K=D\kappa(x_0),
\]

the reduced closed-loop Jacobian is

\[
A_{\rm cl}=A_r+B_{u,r}K.
\]

## E.4 When the parameter-feedback lemma survives

The exact necessary condition along the controller directions is

\[
B_{u,r}K=0.
\]

A convenient sufficient condition, in shifted coordinates \(\xi=x-x_0\), is

\[
F(0,u,w_0)=0
\quad\text{for every nearby feasible }u.
\]

Then

\[
F_u(0,u_0,w_0)K=0,
\]

and

\[
A_{\rm cl}=A_r.
\]

A stronger structural condition is that, after algebraic elimination,

\[
\dot\xi=A_r(u)\xi+o(\|\xi\|)
\]

with no action-dependent affine term. Then the Task B argument applies to the reduced ODE.

## E.5 Failure caused by action-dependent algebraic equations

Even if the differential equation has no direct additive action term,

\[
f_u=0,
\]

the reduced input Jacobian can be nonzero:

\[
B_{u,r}=-f_yg_y^{-1}g_u.
\]

Thus an action that shifts voltages, currents, power-flow variables, or network algebraic constraints can create a direct first-order plant channel after elimination. This is a principal reason the multiplicative \(M/D\) lemma cannot be transferred to a full power-system DAE without calculation.

The accompanying code includes a linear index-1 example with \(f_u=0\) but \(B_{u,r}\ne0\), and verifies the Schur-complement Jacobian by finite differences.

## E.6 Singular or ill-conditioned \(g_y\)

If \(g_y\) is singular:

- the local implicit function \(y=h(x,u,w)\) may not exist;
- the DAE may have index greater than one or changing index;
- hidden constraints and consistency conditions are required;
- the Schur-complement formula is invalid.

If \(g_y\) is ill-conditioned, the formula exists algebraically but can amplify modeling and numerical errors:

\[
\|g_y^{-1}\|=\frac1{\sigma_{\min}(g_y)}.
\]

A credible local result should report \(\sigma_{\min}(g_y)\), a condition number, and a neighborhood over which nonsingularity is preserved.

## E.7 Limiters, saturation, and mode changes

At a fixed active set, use the Jacobian of that mode. At a kink, no unique classical Jacobian may exist. Appropriate tools are:

- one-sided/Bouligand derivatives;
- Clarke generalized Jacobians for bounds;
- saltation matrices for transverse hybrid events;
- explicit mode enumeration or robust active-set envelopes.

Grazing, simultaneous events, chatter, or limiter release/engagement at the nominal point can make sensitivities unbounded or nonunique.

## E.8 Algebraic measurements, measurement filters, and sampled controllers

If a static controller uses algebraic measurements directly,

\[
u=\kappa(x,y),
\]

then \(u\) and \(y\) form an algebraic feedback loop and the formula \(A_r+B_{u,r}D\kappa(x_0)\) cannot be used with a state-only gain. Let

\[
K_x=\kappa_x(x_0,y_0),\qquad K_y=\kappa_y(x_0,y_0).
\]

Linearizing the closed algebraic equation gives

\[
(g_y+g_uK_y)\,\delta y
=-(g_x+g_uK_x)\,\delta x.
\]

If \(g_y+g_uK_y\) is nonsingular, the exact closed-loop state Jacobian is

\[
A_{\rm cl}
=f_x+f_uK_x
-(f_y+f_uK_y)(g_y+g_uK_y)^{-1}(g_x+g_uK_x).
\]

Equivalently, after first eliminating \(y=h(x,u,w)\), one must solve the implicit controller relation \(u=\kappa(x,h(x,u,w))\); this requires nonsingularity of \(I-\kappa_yh_u\). Thus a direct algebraic measurement path can change both well-posedness and first-order authority.

Measurement filters must be added as dynamic states. For example,

\[
\dot z=A_fz+B_fm(x,y),
\qquad
u=\kappa(z,x),
\]

leads to an augmented ODE/DAE Jacobian. The plant-state block may retain limited multiplicative authority, while the augmented controller/filter states and action output have first-order dynamics.

For sampled controllers, first reduce/linearize the continuous DAE in a fixed mode and then construct the exact or certified discrete-time lifted map. Delays and holds belong in the augmented sampled model. Using a continuous-time Jacobian as though it were the 0.2-s map is incorrect.

## E.9 Approximately symmetric and balanced recovered coupling

If a reduced model is forced into

\[
H(s)=s^2M+sD+K_L
\]

but the recovered matrices only approximately preserve common/differential subspaces, exact Task A separation does not apply.

Define the block-diagonal part

\[
H_0=P_cHP_c+P_dHP_d
\]

and the cross perturbation

\[
E=P_cHP_d+P_dHP_c.
\]

If

\[
\|H_0^{-1}E\|<1,
\]

then

\[
H^{-1}-H_0^{-1}=-H_0^{-1}EH^{-1}
\]

and

\[
\|P_dG(s)P_c\|,
\ \|P_cG(s)P_d\|
\le
|s|\,
\frac{\|H_0^{-1}\|^2\|E\|}
{1-\|H_0^{-1}E\|}.
\]

This is a frequency-dependent perturbation bound. It becomes weak near poles or when the resolvent is ill-conditioned. It does not turn approximate balance into exact separation.

Useful balance diagnostics are

\[
\|L\mathbf1\|,
\qquad
\|\mathbf1^\top L\|,
\qquad
\|L-L^\top\|,
\]

and, more directly,

\[
\|P_dLP_c\|,
\qquad
\|P_cLP_d\|.
\]

## E.10 Manuscript-safe wording

> **Lemma (local index-1 DAE reduction).** Let \((x_0,y_0,u_0,w_0)\) be an equilibrium of \(\dot x=f(x,y,u,w)\), \(0=g(x,y,u,w)\), and assume \(f,g\) are continuously differentiable and \(g_y\) is nonsingular at the equilibrium. Then the algebraic state can be eliminated locally, and the reduced Jacobians are
> \[
> A_r=f_x-f_yg_y^{-1}g_x,
> \quad
> B_{u,r}=f_u-f_yg_y^{-1}g_u,
> \quad
> B_{w,r}=f_w-f_yg_y^{-1}g_w.
> \]
> Under state feedback \(u=\kappa(x)\), the reduced closed-loop Jacobian is \(A_r+B_{u,r}D\kappa(x_0)\). The limited-authority multiplicative-parameter lemma survives only when \(B_{u,r}D\kappa(x_0)=0\), for example when the reduced vector field vanishes at the shifted origin for every nearby feasible parameter value. Action dependence in the algebraic equations can make \(B_{u,r}\ne0\) even when \(f_u=0\).

## E.11 Forbidden stronger wording

Do not write:

- “The ODE parameter-feedback lemma automatically applies to the DAE.”
- “A nonsingular \(g_y\) at one numerical point proves a uniformly valid reduction.”
- “Action-dependent algebraic equations do not affect first-order authority.”
- “A limiter-active Jacobian applies across limiter mode changes.”
- “An approximately symmetric coupling matrix satisfies the exact separation theorem.”
- “A continuous-time Jacobian is the sampled 0.2-s closed-loop map.”

## E.12 Additional information needed for a stronger result

1. Full DAE equations, variable partition, and equilibrium.
2. Numerical or symbolic matrices \(f_x,f_y,f_u,f_w,g_x,g_y,g_u,g_w\).
3. Singular values and condition number of \(g_y\) over an operating neighborhood.
4. Exact action path through converter and network algebraic equations.
5. Limiter, saturation, relay, and protection active-set definitions.
6. Whether the controller uses \(x\), algebraic measurements \(y\), or filtered measurements, together with \(\kappa_x,\kappa_y\).
7. Filter, observer, communication, and sample/hold states.
8. The recovered reduced coupling matrix and balance/symmetry residuals.
9. A certified discretization or exact sampled linear model.

---

# Final separation of proof, observation, mechanism, and open questions

| Category | Statement | Status and boundary |
|---|---|---|
| **Mathematically proved** | In the ideal LTI model with full common/differential channels, diagonal nonsingular \(M,D\), and coupling that preserves the two subspaces, exact separation is equivalent to \(M=mI,D=dI\). | Exact rational-matrix theorem. Under the original symmetric model, either one cross block alone suffices. |
| **Mathematically proved** | Zero-bias multiplicative parameter feedback has plant-state Jacobian \(A(u_0)\). | Local first-order statement at the zero/shifted equilibrium; not a finite-amplitude impossibility. |
| **Mathematically proved** | A valid index-1 DAE reduction has \(A_r=f_x-f_yg_y^{-1}g_x\) and \(B_{u,r}=f_u-f_yg_y^{-1}g_u\). | Requires nonsingular \(g_y\) and a fixed differentiable mode. |
| **Mathematically proved under stated regularity** | Two locally Lipschitz zero-bias multiplicative controllers differ by \(O(\varepsilon^2)\) on a fixed finite horizon with a common active mode. | The antisymmetric difference may also be \(O(\varepsilon^2)\); cubic requires extra \(C^3\) assumptions. |
| **Mathematically proved as certificate logic** | A verified conic dual lower bound \(t_L>1\) on the optimum, or a Farkas ray, proves infeasibility of the exact bounded Youla/SLS class. | Does not extend beyond the declared plant, class, scenarios, horizon, or uncertainty set. |
| **Empirically observed in the supplied record** | The deterministic direct-\(M/D\) law improves the two development endpoints by 60.79% and 64.13% relative to zero action; the finite nine-law outcome-seeing oracle gives 0% further improvement on four evaluation profiles. | Empirical record only; not converted into a theorem of global optimality. |
| **Empirically observed in the supplied record** | The three TD3/MATD3 arms have endpoint multiples 4.12/2.92, 4.16/3.13, and 5.09/3.30 relative to the deterministic cross/differential endpoints and fail common/action guards. | Evidence about the tested implementations, seeds, and training protocol only. |
| **Empirically observed in the supplied record** | The energy-port controller at \(K=3.5\) reaches \((r_d,r_{cross})=(0.938947,0.539791)\) on development and \((0.938218,0.793730)\) on the frozen unseen bank, with all guards. | Directly rules out any universal theorem claiming all finite-order LTI, all causal, or all decoupling-oriented controllers are infeasible. |
| **Plausible but unisolated mechanism** | Heterogeneous diagonal \(M,D\) mix common and differential channels in the ideal model. | Structural mechanism is proved in the ideal model; its quantitative responsibility in the nonlinear DAE remains unisolated. |
| **Plausible but unisolated mechanism** | Zero-bias direct \(M/D\) feedback may have weak small-signal authority while finite-amplitude nonlinear effects dominate. | Consistent with Task B/C, but requires amplitude-scaling data on the actual implementation. |
| **Plausible but unisolated mechanism** | Decoder asymmetry and absolute values generate different one-sided quadratic coefficients. | Mathematically possible and generic; actual coefficients require directional trajectory experiments. |
| **Plausible but unisolated mechanism** | Energy-port actuation succeeds because it creates an additive first-order channel and aligns with ring differential modes. | Additive authority is proved in principle; alignment and causal mechanism require identified plant/trajectory analysis. |
| **Open question** | Can a precisely defined local finite-order controller class enter \(\mathcal Q\) on the declared finite scenario bank? | Requires the actual plant, metric, class, and conic certificate data. |
| **Open question** | Is the actual signed-pair difference first-, second-, or third-order over a common active-mode region? | Requires the geometric amplitude experiment and an explicit normalizer. |
| **Open question** | Does DAE elimination preserve multiplicative-only action authority? | Requires \(f_y,g_y,g_u,f_u\) at the operating point. |
| **Open question** | How robust are the observed energy-port results to plant uncertainty and broader unseen profiles? | Not answered by the finite empirical bank or a nominal local model. |

---

# Reproducibility package

The accompanying files are deliberately separated into theorem checks, synthetic diagnostics, and a certificate template. `coverage_matrix.md` maps every requested subtask to the corresponding report section, code, and data.

## Code

- `code/vsg_audit_verify.py`
  - verifies the high-frequency expansion;
  - evaluates homogeneous separation;
  - constructs the directed-unbalanced, rank-deficient-output, single-frequency, and nondiagonal counterexamples;
  - verifies the multiplicative/additive and sampled Jacobians by finite differences;
  - generates synthetic \(O(\varepsilon)\), \(O(\varepsilon^2)\), and \(O(\varepsilon^3)\) signed-probe data;
  - checks the approximate block-separation resolvent bound;
  - verifies the index-1 DAE Schur complement for state feedback and direct algebraic-measurement feedback.
- `code/symbolic_exact_checks.py`
  - uses exact rational arithmetic and symbolic \(s\) to verify the Laurent coefficients, counterexample identities, multiplicative/additive Jacobians, decoder signed components, and DAE Schur complements.
- `code/run_all_checks.py`
  - regenerates all numerical, symbolic, and synthetic-certificate outputs;
  - enforces package-level assertions and writes `data/qa_summary.json`.
- `code/bounded_certificate_template.py`
  - validates an affine closed-loop map schema;
  - formulates the target-scaling SOCP when CVXPY and a conic solver are installed;
  - exports candidate primal residuals and per-constraint dual values;
  - independently recomputes primal feasibility from the returned \((q,t)\);
  - independently checks LP and nonnegative/SOC product-cone Farkas certificates;
  - includes a small exact synthetic certificate with \(t_\star=24/19>1\).

## Data

- `data/audit_numeric_results.json` — numerical theorem/counterexample checks.
- `data/symbolic_exact_results.json` — exact SymPy theorem/counterexample checks.
- `data/high_frequency_expansion.csv` — observed \(s^{-2}\) and \(s^{-3}\) truncation-error scaling.
- `data/approximate_separation_bound.csv` — numerical sanity check of the resolvent perturbation bound.
- `data/signed_probe_synthetic.csv` — synthetic order diagnostics; **not VSG experiment data**.
- `data/dae_jacobian_check.csv` — state-feedback and algebraic-measurement DAE Jacobians with finite-difference checks.
- `data/certificate_affine_map_template.json` — schema with synthetic arrays to replace with actual Youla/SLS maps.
- `data/synthetic_lp_certificate.json` — exact LP Farkas demonstration; **not a VSG infeasibility result**.
- `data/conic_farkas_certificate_example.json` and `data/conic_farkas_verification.json` — synthetic product-cone certificate input and independent verification output.
- `data/qa_summary.json` — package-level assertion summary.

## Commands

```bash
python code/run_all_checks.py

# Or run the components separately:
python code/vsg_audit_verify.py --output-dir data
python code/symbolic_exact_checks.py --output data/symbolic_exact_results.json
python code/bounded_certificate_template.py \
  --synthetic-demo \
  --output data/synthetic_lp_certificate.json

python code/bounded_certificate_template.py \
  --verify-farkas data/conic_farkas_certificate_example.json \
  --output data/conic_farkas_verification.json
```

For an actual SOCP after replacing the template arrays:

```bash
python code/bounded_certificate_template.py \
  --spec data/certificate_affine_map_actual.json \
  --solver MOSEK \
  --output data/certificate_solution.json
```

A solver output remains a candidate until its dual variables, residuals, separation/lower-bound margin, and uncertainty robustness are independently checked.

---

# References used for the control-framework formulation

1. D. C. Youla, H. A. Jabr, and J. J. Bongiorno, Jr., “Modern Wiener–Hopf Design of Optimal Controllers—Part II: The Multivariable Case,” *IEEE Transactions on Automatic Control*, 21(3), 319–338, 1976.
2. M. Rotkowitz and S. Lall, “A Characterization of Convex Problems in Decentralized Control,” *IEEE Transactions on Automatic Control*, 51(2), 274–286, 2006.
3. Y.-S. Wang, N. Matni, and J. C. Doyle, “A System Level Approach to Controller Synthesis,” *IEEE Transactions on Automatic Control*, 64(10), 4079–4093, 2019.
4. J. Anderson, J. C. Doyle, S. H. Low, and N. Matni, “System Level Synthesis,” *Annual Reviews in Control*, 47, 364–393, 2019.
5. F. H. Clarke, *Optimization and Nonsmooth Analysis*, SIAM, 1990.
6. N. J. Kong, J. J. Payne, J. Zhu, and A. M. Johnson, “Saltation Matrices: The Essential Tool for Linearizing Hybrid Dynamical Systems,” *Proceedings of the IEEE*, 112(6), 585–608, 2024.
7. K. E. Brenan, S. L. Campbell, and L. R. Petzold, *Numerical Solution of Initial-Value Problems in Differential-Algebraic Equations*, SIAM, 1996.
8. MOSEK ApS, *MOSEK Modeling Cookbook*, sections on conic duality, Slater regularity, and Farkas infeasibility certificates.


