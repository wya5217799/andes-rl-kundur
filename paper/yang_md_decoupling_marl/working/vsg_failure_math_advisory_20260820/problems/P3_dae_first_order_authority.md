# P3 — First-order authority of multiplicative M/D feedback in the index-1 DAE

**Type label: (P)**

## Headline result

For a semi-explicit index-1 DAE, the effective first-order action channel is exactly

$$
B_{u,r}=f_u-f_y g_y^{-1}g_u.
$$

For the usual swing-equation structure at a synchronous power-balanced equilibrium, the direct derivatives with respect to inertia and damping vanish. If $M$ and $D$ also do not enter the algebraic equations, then $g_u=0$ and therefore $B_{u,r}=0$: algebraic elimination does not create first-order authority by itself. The package does not contain the actual ANDES DAE Jacobians or a finite-difference measurement, so whether the implemented Object A satisfies these conditions remains unresolved. The correct contribution is a conditional lemma plus an executable measurement recipe, not a claim that the channel is active or absent in the project plant.

## Hard facts

The environment interpolates the action-selected $M$ and $D$ values and writes them to `GENCLS` before each TDS substep [P3-S01]. Its diagnostic state derivative uses the package-source swing form

$$
\dot\omega_i=\frac{P_{m,i}-P_{e,i}-D_i(\omega_i-1)}{M_i}
$$

with a numerical denominator guard in code [P3-S02]. The imported theory audit states the reduced DAE channel $B_{u,r}=f_u-f_yg_y^{-1}g_u$ and explicitly records that the actual reduced/DAE Jacobians are not supplied [P3-S03]. These are package facts. No numerical value of $B_{u,r}$ is sealed.

## Assumption set

Let the local plant be represented near a registered equilibrium by

$$
\dot x=f(x,y,u),\qquad 0=g(x,y,u),
$$

where $x$ contains differential states, $y$ contains algebraic network variables after fixing the angle-reference gauge, and $u$ contains the multiplicative $M/D$ command coordinates. Assume:

1. $f$ and $g$ are continuously differentiable in a neighborhood of $(x_\star,y_\star,u_\star)$.
2. The gauge-fixed algebraic Jacobian $g_y(x_\star,y_\star,u_\star)$ is nonsingular; equivalently, the local DAE is index one on the selected active mode.
3. The controlled swing rows have the form
   $$
   f_{\omega_i}=\frac{P_{m,i}-P_{e,i}(x,y,u)-D_i(u)(\omega_i-\omega_s)}{M_i(u)}.
   $$
4. The equilibrium is synchronous and power balanced on those rows: $\omega_i=\omega_s$ and $P_{m,i}=P_{e,i}$.
5. Any projection, saturation, limiter, or feasibility map has one fixed differentiable active mode locally. If the active mode changes under the perturbation, the classical Jacobian proposition does not apply.

## Proposition P3.1 — index-1 Schur input channel

Under Assumptions 1–2, the locally reduced ODE obtained by eliminating $y$ has Jacobians

$$
A_r=f_x-f_y g_y^{-1}g_x,
\qquad
B_{u,r}=f_u-f_y g_y^{-1}g_u.
$$

### Proof

By the implicit-function theorem, $g(x,h(x,u),u)=0$ defines $y=h(x,u)$ locally, with

$$
h_x=-g_y^{-1}g_x,\qquad h_u=-g_y^{-1}g_u.
$$

The reduced vector field is $F(x,u)=f(x,h(x,u),u)$. Applying the chain rule gives

$$
F_x=f_x+f_yh_x=f_x-f_yg_y^{-1}g_x,
$$

and

$$
F_u=f_u+f_yh_u=f_u-f_yg_y^{-1}g_u.
$$

## Proposition P3.2 — conditional zero first-order M/D authority

Under Assumptions 1–5, additionally suppose that:

- $M_i$ and $D_i$ enter no algebraic equation directly, so $g_u=0$ at the equilibrium; and
- $P_{m,i}$ and $P_{e,i}$ have no direct dependence on the $M/D$ command at fixed $(x,y)$.

Then the reduced first-order channel from the $M/D$ command is zero at the synchronous equilibrium:

$$
B_{u,r}=0.
$$

### Proof

For each controlled swing row,

$$
\frac{\partial f_{\omega_i}}{\partial M_i}
=-\frac{P_{m,i}-P_{e,i}-D_i(\omega_i-\omega_s)}{M_i^2},
\qquad
\frac{\partial f_{\omega_i}}{\partial D_i}
=-\frac{\omega_i-\omega_s}{M_i}.
$$

Both derivatives vanish under Assumption 4. By the additional structural hypothesis, the remaining entries of $f_u$ vanish, and $g_u=0$. Proposition P3.1 then gives $B_{u,r}=0$.

## Exact routes by which $B_{u,r}$ can be nonzero

The proposition identifies the complete local routes:

1. **Direct differential route:** $f_u\ne0$. This occurs away from power balance, away from synchronous speed, when the action directly changes mechanical/electrical power, or when another differential row contains an additive action term.
2. **Algebraic Schur route:** $g_u\ne0$ and $f_yg_y^{-1}g_u\ne0$. This requires the action to enter algebraic power/current balance, a static converter relation, an active limiter equation, or another algebraic constitutive law. Merely having $f_y\ne0$ through electrical-power sensitivity is insufficient when $g_u=0$.
3. **Nonsmooth route:** an active-set change can produce a directional or generalized derivative even when the smooth-mode Jacobian is zero. That is a separate piecewise-smooth statement and must not be reported as the classical $B_{u,r}$.
4. **Gauge or singularity artifact:** using an unfixed angle gauge can make $g_y$ singular and the Schur expression undefined. A slack/reference condition or a projection to the balanced subspace is required before interpretation.

## Interpretation, kept separate from fact

The source structure makes a zero smooth channel plausible, because the action is written as $M/D$ parameters and the diagnostic swing derivative has the multiplicative form [P3-S01–P3-S02]. It is nevertheless not a measurement of the actual DAE Jacobian. In particular, the package does not expose the internal `GENCLS` algebraic residuals, network Jacobians, active-set derivatives, or the derivative of the feasibility-native action map. The correct current answer to “is $B_{u,r}$ nonzero for Object A?” is therefore **not identified from the shipped evidence**.

If Proposition P3.2 is verified, the local policy slope cannot create an additive first-order plant-state channel at the synchronous equilibrium through $M/D$ modulation; its leading effect is state-dependent/bilinear or higher order. If the finite-difference measurement instead finds a stable nonzero $B_{u,r}$ and the Schur reconstruction agrees, the project has identified the precise algebraic or direct route that completes the limitation in the ODE lemma.

## Finite-difference DAE verification plan

Let $e_j$ be one action coordinate and let $h$ be a decreasing perturbation magnitude (**HYPOTHETICAL numerical design**, to be registered against solver tolerance).

### Direct reduced-channel measurement

For each $j$:

1. Freeze $x=x_\star$ and set $u_\pm=u_\star\pm he_j$.
2. Starting from $y_\star$, re-solve the algebraic equations $g(x_\star,y_\pm,u_\pm)=0$ with the same angle gauge and the same active mode.
3. Evaluate the differential residuals $f_\pm=f(x_\star,y_\pm,u_\pm)$ without advancing time.
4. Form
   $$
   \widehat B^{\mathrm{FD}}_{u,r}(:,j)=\frac{f_+-f_-}{2h}.
   $$
5. Repeat over a geometric $h$ sequence. A classical derivative is supported only if the estimate converges before solver noise dominates.

### Independent Schur reconstruction

Measure $f_u,f_y,g_u,g_y$ by centered differences at the same equilibrium and form

$$
\widehat B^{\mathrm{Schur}}_{u,r}
=
\widehat f_u-
\widehat f_y\widehat g_y^{-1}\widehat g_u.
$$

Record the condition number and residual of the $g_y$ solves; never explicitly invert a poorly conditioned matrix. Compare $\widehat B^{\mathrm{FD}}_{u,r}$ with $\widehat B^{\mathrm{Schur}}_{u,r}$ column by column. Log action projection, saturation, limiter status, and algebraic active-set identity for every perturbation.

### Decision rule

A nonzero smooth channel is supported when: (i) the centered derivative is stable over the registered $h$ range; (ii) it exceeds a preregistered numerical/noise bound; (iii) the Schur and direct estimates agree; and (iv) the active mode remains unchanged. It is refuted at the tested equilibrium when a registered upper confidence bound on every relevant entry or induced norm lies below the project’s materiality threshold. Both the numerical noise bound and materiality threshold are currently **HYPOTHETICAL** because no sealed values are provided.

## Reduced-model identifiability

Consider the deviation model

$$
\dot\theta=\omega,\qquad
M\dot\omega+D\omega+L\theta=B_w w+e.
$$

### What is identifiable in principle

- With calibrated $w$, measured $(\theta,\omega,\dot\omega)$, known $M,D$, and persistently exciting probes, $L$ is identifiable on the angle-balanced subspace. The common angle is a gauge: $\theta$ and $\theta+c\mathbf 1$ are observationally equivalent when $L\mathbf 1=0$.
- Joint recovery of diagonal $M,D$ and $L$ is possible only if the stacked regressor has full column rank after imposing the gauge and structural constraints. Collinearity between $\dot\omega$, $\omega$, and $\theta$ destroys uniqueness.
- Symmetry $L=L^\top$, balance $L\mathbf 1=0$, and Laplacian sign structure are testable model restrictions, not facts to impose silently. Uncalibrated input scale creates an additional scaling ambiguity.

### Residuals that should be reported

For an estimate $(\widehat M,\widehat D,\widehat L)$, report at least

$$
e_{\mathrm{dyn}}=B_ww-\widehat M\dot\omega-\widehat D\omega-\widehat L\theta,
$$

$$
e_{\mathrm{sym}}=\widehat L-\widehat L^\top,
\qquad
e_{\mathrm{bal}}=\widehat L\mathbf 1,
$$

plus out-of-sample trajectory prediction error and the smallest singular value of the constrained regressor. A claim that the exact-Laplacian premise is consistent with the plant should use a preregistered confidence set and model-error tolerance; small in-sample least-squares residual alone is not enough. Exact equality cannot be certified from noisy trajectories without a structural model or interval error bounds.

## Evidence binding

No experimental scalar is asserted for $B_{u,r}$ or the recovered $L$. The only implementation facts used are the package-source records [P3-S01–P3-S03]. All finite-difference step sizes, numerical tolerances, materiality thresholds, excitation amplitudes, and model-order choices are **HYPOTHETICAL** until registered and sealed.

## Missing quantity and minimal experiment

The package lacks the equilibrium residual vectors, $f_x,f_y,f_u,g_x,g_y,g_u$, algebraic conditioning, action-map derivative, active-mode log, and signed-probe trajectories with calibrated inputs. The minimal authority experiment is the equilibrium re-solve/centered-difference procedure above. The minimal identifiability experiment is a persistently exciting signed-probe record containing synchronized $w$, $\theta$, $\omega$, $\dot\omega$, operating-point metadata, and active-mode status, followed by constrained identification with held-out prediction.

## Paper-ready wording

For a continuously differentiable semi-explicit index-1 DAE $\dot x=f(x,y,u)$, $0=g(x,y,u)$ with nonsingular gauge-fixed $g_y$, algebraic elimination gives the exact reduced input Jacobian $B_{u,r}=f_u-f_yg_y^{-1}g_u$. For swing rows of the form $[P_m-P_e-D(\omega-\omega_s)]/M$, the direct derivatives with respect to $M$ and $D$ vanish at a synchronous power-balanced equilibrium. Hence, if the $M/D$ command does not enter the algebraic equations or any other differential residual directly, then $g_u=0$, $f_u=0$, and multiplicative $M/D$ feedback has no additive first-order reduced-state authority at that equilibrium. A nonzero first-order channel can arise only through direct action dependence, action-dependent algebraic balance, or a nonsmooth active-mode change. The present package confirms that the implementation updates live `GENCLS` $M/D$ parameters and uses the corresponding swing form [P3-S01–P3-S02], but it does not contain the actual ANDES Jacobians [P3-S03]. We therefore state the result conditionally and prescribe an equilibrium algebraic re-solve with centered finite differences, independently checked against the Schur reconstruction, before asserting whether the channel is active in Object A.
