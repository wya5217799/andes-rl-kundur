# P1-P3 Camera-Ready Mathematics Appendix

**Scope:** bounded propositions and repository-side verification plans for the 2026-09-07 camera-ready window.  
**Evidence convention:** every empirical number is indexed in `../evidence/evidence_register.csv`; unsealed design values are HYPOTHETICAL.

## Editorial boundary

The three results below are written at the strongest level supported by the frozen package. P1 does not identify a stability-margin mechanism, P2 does not equate endpoint crossing with instability, and P3 does not classify the implemented DAE channel before Jacobian/finite-difference verification.



---

## P1 — Relaxed-plant failure block: what is and is not identified

**Type label: (P)**

### Headline result

The sealed evidence supports a paper-grade **ratio-sensitivity decomposition**, not a gain-margin or phase-margin diagnosis. The relaxed block fails because the fixed candidate achieves only a small reduction relative to that block's local reference; the package does not identify whether this comes from plant-loop sensitivity, movement of the local-reference denominator, or both. The channel-detuning explanation is separately refuted by R437.

### Hard facts

The constructive arm is `bandpass_k3p5` [P1-E01]. It records $r_d=0.9389467910702068$ and $r_{\mathrm{cross}}=0.5397906554502304$ in R408 [P1-E02–P1-E03], and $r_d=0.9382180713649944$ and $r_{\mathrm{cross}}=0.7937304481638234$ in the R409 held-out gate [P1-E04–P1-E05]. The R415 ceilings are $r_d\le 0.95$, $r_{\mathrm{cross}}\le 1.1$, with a strict cross ceiling of $0.95$ [P1-E06–P1-E08].

| R415 block | sealed $(M,D_i)$ | $r_d$ | local $E_d$ | candidate $E_d=r_dE_{d,L}$ | relative reduction $1-r_d$ | outcome |
|---|---:|---:|---:|---:|---:|---|
| conditions | $(200,100)$ [P1-E09–P1-E10] | 0.9322838738147555 [P1-E11] | 0.0005433139119660554 [P1-E13] | 0.0005065227985451632 [P1-D01] | 0.06771612618524447 [P1-D03] | pass [P1-E16] |
| relaxed | $(170,115)$ [P1-E17–P1-E18] | 0.9712251032133927 [P1-E19] | 0.00021018948180799598 [P1-E21] | 0.00020414130116334044 [P1-D04] | 0.028774896786607274 [P1-D06] | fail [P1-E24] |
| stiff | $(230,85)$ [P1-E25–P1-E26] | 0.907962726673478 [P1-E27] | 0.00030010287872978 [P1-E29] | 0.0002724822280540511 [P1-D07] | 0.092037273326522 [P1-D09] | pass [P1-E32] |

All three candidate guard bundles pass [P1-E15, P1-E23, P1-E31]. The three blocks do **not** use a matched disturbance/probe bank: their `condition_id` values differ under `results/research_loop/r415_energy_port_extra_banks/formal_analysis.json#/blocks/<block>/block/disturbance_conditions` and `#/probe_condition`. Consequently, differences across these rows are not finite differences with respect to $M$ or $D$.

R437 reports a relaxed-block peak at $0.44921875\,\mathrm{Hz}$ and a spectral-window fraction of $0.5866071101135871$ [P1-E34–P1-E35], versus passing-block peak frequencies $[0.33203125,0.390625]\,\mathrm{Hz}$ and window fractions $[0.5288535035245917,0.5034156773618179]$ [P1-E36–P1-E37]. Its registered mechanism verdict is `REFUTED` [P1-E38], with the stated reason that the relaxed spectrum remains inside the tested window in the same sense as the passing blocks [P1-E39].

### Assumption set

Let $\rho$ denote a scalar plant parameter or a differentiable path through $(M,D)$. Assume:

1. For a fixed disturbance/probe ensemble, the candidate and local-reference differential output maps $G_K(\mathrm{j}\omega;\rho)$ and $G_L(\mathrm{j}\omega;\rho)$ are differentiable in $\rho$.
2. The weighted energies $E_K(\rho)=\lVert G_K(\rho)\rVert_W^2$ and $E_L(\rho)=\lVert G_L(\rho)\rVert_W^2$ are positive, with the same nonnegative weighting operator $W$ and the same excitation ensemble.
3. The reported endpoint is $r_d(\rho)=E_K(\rho)/E_L(\rho)$.
4. The scalar-loop specialization below is used only when the measured candidate channel can be written as $G_K=P/(1+PK)$ with fixed $K$ and a well-posed loop.
5. The second-order swing transfer used later is **HYPOTHETICAL** until a reduced-model identification or Jacobian export is sealed.

### Proposition P1.1 — exact log-sensitivity decomposition

Under Assumptions 1–3,

$$
\frac{\partial \log r_d}{\partial \rho}
=
2\,\operatorname{Re}\frac{\langle G_K,\partial_\rho G_K\rangle_W}{\lVert G_K\rVert_W^2}
-
2\,\operatorname{Re}\frac{\langle G_L,\partial_\rho G_L\rangle_W}{\lVert G_L\rVert_W^2}.
$$

Equivalently,

$$
\partial_\rho r_d
=
\frac{\partial_\rho E_K}{E_L}
-r_d\frac{\partial_\rho E_L}{E_L}.
$$

#### Proof

Differentiate $r_d=E_K/E_L$ by the quotient rule. For $E(\rho)=\langle G(\rho),G(\rho)\rangle_W$, differentiability and Hermitian symmetry give $\partial_\rho E=2\operatorname{Re}\langle G,\partial_\rho G\rangle_W$. Dividing by $E_K$ and $E_L$ yields the log form. No control-specific approximation is used.

### Corollary P1.2 — fixed-controller scalar-loop contribution

Under Assumption 4, define $L=PK$ and $S=(1+L)^{-1}$. Then

$$
\partial_\rho\log G_K(\mathrm{j}\omega;\rho)
=S(\mathrm{j}\omega;\rho)\,\partial_\rho\log P(\mathrm{j}\omega;\rho).
$$

Thus the candidate-energy term in Proposition P1.1 is a weighted real projection of plant log-sensitivity through the **complex** sensitivity $S$; magnitude-only spectra do not determine it.

#### Proof

From $G_K=P(1+PK)^{-1}$ with fixed $K$,

$$
\partial_\rho\log G_K
=\partial_\rho\log P-\frac{PK}{1+PK}\partial_\rho\log P
=\frac{1}{1+PK}\partial_\rho\log P.
$$

### HYPOTHETICAL reduced-swing specialization

For the **HYPOTHETICAL** channel

$$
P_d(s;M,D)=\frac{b s}{M s^2+D s+\kappa},
$$

the logarithmic parameter derivatives are

$$
\frac{\partial\log P_d}{\partial\log M}
=-\frac{M s^2}{M s^2+D s+\kappa},\qquad
\frac{\partial\log P_d}{\partial\log D}
=-\frac{D s}{M s^2+D s+\kappa}.
$$

Inserted into Corollary P1.2, these expressions predict the frequency-resolved sign and strength of $M$/$D$ detuning **only after** the complex $S(\mathrm{j}\omega)$ and the matched local-reference sensitivity are measured.

### Interpretation, kept separate from fact

The sealed relaxed row is a **relative-performance** failure: its candidate differential energy is lower than the absolute candidate energies in the other two R415 rows [P1-D01, P1-D04, P1-D07], yet it is closer to its own local-reference energy and therefore exceeds the ratio ceiling. This does not prove that the local denominator caused the failure, because the disturbance/probe identities change with the block. It does prove that “the candidate's absolute differential energy became large” is not a valid description of the three-row table.

R437 removes one proposed explanation—coarse channel-frequency detuning within the registered spectral test—but it does not identify loop phase, gain crossover, Nyquist distance, or sensitivity peak. A PSD peak is not a stability-margin certificate.

### Evidence binding

All sealed and derived values used above are indexed in `evidence/evidence_register.csv`. The numerator reconstructions [P1-D01, P1-D04, P1-D07] are exact products of the corresponding sealed ratio and local energy. No value is back-filled across blocks. The swing transfer and its coefficients are explicitly marked **HYPOTHETICAL**.

### Verification plan

1. Re-run nominal, relaxed, and stiff $(M,D)$ settings on one **identical** signed disturbance/probe bank and one fixed simulation horizon. Preserve the same local-reference controller and normalization.
2. Export complex empirical frequency responses $G_K(\mathrm{j}\omega)$ and $G_L(\mathrm{j}\omega)$, not only PSD magnitudes. If the loop break is well-defined, also export $L(\mathrm{j}\omega)$.
3. Use central differences in $M$ and $D$ with a geometrically decreasing perturbation $h$ (**HYPOTHETICAL numerical design**) and verify convergence of both sides of Proposition P1.1.
4. Decompose the measured derivative into candidate and denominator terms. A candidate-loop mechanism is supported when the first term dominates reproducibly; a reference-normalization mechanism is supported when the second term dominates. Mixed dominance is admissible.
5. Compute phase margin or Nyquist distance only from a verified loop definition. Refute a claimed margin mechanism if the measured margin change has the wrong sign or cannot reproduce the endpoint derivative within uncertainty.

### Missing quantity and minimal experiment

The package lacks: (i) matched-block complex $G_K$ and $G_L$; (ii) a loop-broken complex $L$; (iii) matched finite differences in $M$ and $D$; and (iv) uncertainty estimates. The minimal experiment is a matched nominal/relaxed/stiff small-amplitude signed-probe sweep with complex response estimation for both the candidate and local reference. Without it, a margin-level causal explanation is not solvable from the shipped data.

### Paper-ready wording

For the fixed `bandpass_k3p5` controller, the relaxed R415 block is rigorously characterized as a relative-energy failure rather than an identified stability-margin failure. Writing the registered differential endpoint as $r_d=E_K/E_L$, where $E_K$ and $E_L$ are candidate and local-reference energies under a common excitation and weighting, gives the exact sensitivity identity $\partial_\rho\log r_d=2\operatorname{Re}\langle G_K,\partial_\rho G_K\rangle_W/\lVert G_K\rVert_W^2-2\operatorname{Re}\langle G_L,\partial_\rho G_L\rangle_W/\lVert G_L\rVert_W^2$. In the sealed relaxed block, $r_d=0.9712251032133927$ [P1-E19], while the reconstructed candidate and local energies are $0.00020414130116334044$ and $0.00021018948180799598\,\mathrm{Hz}^2\mathrm{s}$ [P1-D04, P1-E21], respectively; hence the controller supplies only a $0.028774896786607274$ relative reduction [P1-D06], below that required by the registered $0.95$ ceiling [P1-E06]. R437 separately refutes the registered spectral-detuning explanation [P1-E38]. Because the R415 blocks use different disturbance and probe identities and the package contains no complex loop response, these results do not identify an $M$/$D$ derivative, gain margin, phase margin, or universal robustness boundary; those require a matched complex-response finite-difference experiment.


---

## P2 — Discrete controller-delay boundary

**Type label: (P)**

### Headline result

A pure integer delay admits an exact phase-loss and sensitivity-amplification formula. The sealed R440 data establish only that the tested one-step and two-step implementations violate the differential endpoint while retaining the registered guards. They do not provide the complex nominal loop, crossover frequency, or a same-bank zero-delay case, so neither an analytic time-delay margin nor a causal phase-margin explanation can be numerically identified from the package.

### Hard facts

The differential ceiling is $0.95$ [P1-E06]. R440 records:

| delay | $r_d$ | excess above ceiling | $r_{\mathrm{cross}}$ | candidate/local $E_d$ | guards | unit outcome |
|---:|---:|---:|---:|---:|---|---|
| 1 step [P2-E01] | 0.9502787849106537 [P2-E02] | 0.0002787849106536955 [P2-D01] | 0.6055328645068879 [P2-E03] | 0.00039037026048215306 / 0.0004107955125177883 [P2-E06–P2-E07] | pass [P2-E04] | fail [P2-E05] |
| 2 steps [P2-E10] | 0.9893270595363578 [P2-E11] | 0.039327059536357845 [P2-D02] | 0.6405191344833928 [P2-E12] | 0.0004438716827728703 / 0.0004486602064446596 [P2-E15–P2-E16] | pass [P2-E13] | fail [P2-E14] |

The overall registered verdict is `BOUNDED-FAILURE` [P2-E19]. The physical duration represented by one step is not a sealed scalar in the R440 JSON files; any conversion from steps to seconds in this report would therefore be **HYPOTHETICAL** under the intake contract.

### Assumption set

Assume:

1. A scalar, well-posed, discrete-time negative-feedback loop has nominal complex loop transfer $L_0(e^{\mathrm{j}\Omega})$.
2. An integer computational delay of $n$ samples enters only as the multiplicative factor $e^{-\mathrm{j}n\Omega}$ in that loop; plant, controller coefficients, sampling, excitation, and endpoint denominator are otherwise unchanged.
3. The output channel of interest has a numerator unaffected by the delay, so its delay dependence is carried by the sensitivity denominator.
4. For the phase-margin corollary, a regular unit-gain crossover $\Omega_c$ and a locally dominant crossover exist. This is a local statement, not a global Nyquist certificate.
5. Converting sample delay to physical time requires a verified sample period; no numerical period is assumed here.

### Proposition P2.1 — exact integer-delay sensitivity ratio

Let

$$
S_n(e^{\mathrm{j}\Omega})
=\frac{1}{1+L_0(e^{\mathrm{j}\Omega})e^{-\mathrm{j}n\Omega}},
\qquad
L_0(e^{\mathrm{j}\Omega})=\ell(\Omega)e^{\mathrm{j}\phi(\Omega)}.
$$

Then, at every frequency where the loop is well posed,

$$
\frac{|S_n|^2}{|S_0|^2}
=
\frac{|1+L_0|^2}{|1+L_0e^{-\mathrm{j}n\Omega}|^2}
=
\frac{1+\ell^2+2\ell\cos\phi}
{1+\ell^2+2\ell\cos(\phi-n\Omega)}.
$$

If the measured output channel is $G_n=N S_n$ with delay-independent numerator $N$, the same identity holds for $|G_n/G_0|^2$.

#### Proof

Substitute the delayed loop into the sensitivity definition, take the squared modulus, and use $|1+\ell e^{\mathrm{j}\psi}|^2=1+\ell^2+2\ell\cos\psi$.

### Corollary P2.2 — infinitesimal delay direction

For a continuous delay parameter $\tau$ in $L_\tau(\mathrm{j}\omega)=L_0(\mathrm{j}\omega)e^{-\mathrm{j}\omega\tau}$,

$$
\frac{\partial}{\partial\tau}\log|S_\tau(\mathrm{j}\omega)|^2
=
-\frac{2\ell\omega\sin(\phi-\omega\tau)}
{1+\ell^2+2\ell\cos(\phi-\omega\tau)}.
$$

The sign is frequency- and phase-dependent. Delay is therefore not guaranteed to increase every weighted output energy monotonically, even though it reduces phase at each positive frequency.

### Corollary P2.3 — local phase-margin loss at a regular crossover

At a nominal unit-gain crossover $\Omega_c$, write the nominal loop phase as $-\pi+\mathrm{PM}_0$. The delayed local phase margin is

$$
\mathrm{PM}_n=\mathrm{PM}_0-n\Omega_c,
$$

and

$$
|S_n(e^{\mathrm{j}\Omega_c})|
=\frac{1}{2|\sin(\mathrm{PM}_n/2)|}.
$$

Under the additional single-crossover regularity assumptions, the local phase-margin boundary is $n=\mathrm{PM}_0/\Omega_c$. This is **not** the registered endpoint boundary: a weighted energy ratio may cross its ceiling while the loop remains stable, exactly as the R440 guard-passing rows allow.

### Endpoint-level consequence

For a fixed excitation weighting $W$ and a fixed local-reference denominator $E_L$, the delayed differential endpoint can be written

$$
r_d(n)=\frac{\lVert N S_n\rVert_W^2}{E_L}.
$$

Proposition P2.1 therefore converts a measured complex loop $L_0$ into a predicted endpoint curve. Without $L_0$, only the two sealed endpoint samples are known. In particular, comparing R440 to R408 would mix experiment banks and cannot supply the missing zero-delay value for this curve.

### Interpretation, kept separate from fact

The one-step result is a narrowly missed endpoint, not evidence of instability: the differential ratio exceeds the ceiling by the sealed amount [P2-D01] while all registered guards pass [P2-E04]. The two-step case moves farther above the ceiling [P2-D02], which is directionally consistent with phase loss but does not establish phase loss as the causal mechanism. The cross endpoint remains below its strict ceiling in both cases [P2-E03, P2-E12, P1-E08], so the observed boundary is differential-channel specific within this test.

### Evidence binding

All numerical statements are linked to `evidence/evidence_register.csv`. The excess values [P2-D01–P2-D02] are exact subtractions from the sealed $0.95$ ceiling. No zero-delay value, sample period, gain crossover, phase margin, or loop transfer is inferred. Any future physical-time conversion is **HYPOTHETICAL** until its timing field is sealed.

### Verification plan

1. Add a same-bank zero-delay record with the identical disturbances, probes, local reference, horizon, and endpoint code used by `delay_1.json` and `delay_2.json`.
2. Record the exact control sample period and the location of the delay in the signal path.
3. Break or identify the loop and export $L_0(e^{\mathrm{j}\Omega})$ as a complex array over the endpoint-relevant band.
4. Compute $S_n$ from Proposition P2.1 for each tested integer $n$, propagate it through the measured numerator, and predict $r_d(n)$ with no fitted phase offset.
5. Support the phase-loss mechanism if the predicted endpoint curve and measured same-bank curve agree within registered uncertainty and the inferred crossover phase decreases by $n\Omega_c$. Refute it if the complex-loop prediction has the wrong endpoint direction or cannot explain the measured change.
6. Report separately: endpoint boundary, local phase-margin boundary, and nonlinear/guard boundary. Do not substitute one for another.

### Missing quantity and minimal experiment

The missing quantities are the same-bank $n=0$ endpoint, the exact sample period, the complex nominal loop $L_0$, the output numerator/weighting map, and uncertainty across repeated runs. The minimal experiment is a registered integer-delay sweep including zero delay, accompanied by one complex loop-identification export. Without those quantities, the package supports an exact symbolic delay law and two bounded failure observations, but no numerical analytic delay margin.

### Paper-ready wording

For a fixed discrete-time feedback loop with nominal complex loop transfer $L_0(e^{\mathrm{j}\Omega})$, an integer delay of $n$ samples changes the sensitivity exactly to $S_n=(1+L_0e^{-\mathrm{j}n\Omega})^{-1}$, giving $|S_n/S_0|^2=(1+\ell^2+2\ell\cos\phi)/(1+\ell^2+2\ell\cos(\phi-n\Omega))$ for $L_0=\ell e^{\mathrm{j}\phi}$. At a regular unit-gain crossover, this corresponds locally to the phase-margin loss $\mathrm{PM}_n=\mathrm{PM}_0-n\Omega_c$; however, the registered energy endpoint may fail before any stability boundary is reached. In R440, the one-step and two-step cases yield $r_d=0.9502787849106537$ and $0.9893270595363578$ [P2-E02, P2-E11], respectively, both above the registered $0.95$ ceiling [P1-E06], while their no-harm guards remain satisfied [P2-E04, P2-E13]. These observations establish a bounded controller-delay failure of the differential endpoint, not an instability claim. Because the sealed files omit a same-bank zero-delay case, the physical sample period, and the complex loop response, they do not identify a numerical delay margin or prove that phase loss is the sole mechanism; those claims require the registered complex-response delay sweep specified here.


---

## P3 — First-order authority of multiplicative M/D feedback in the index-1 DAE

**Type label: (P)**

### Headline result

For a semi-explicit index-1 DAE, the effective first-order action channel is exactly

$$
B_{u,r}=f_u-f_y g_y^{-1}g_u.
$$

For the usual swing-equation structure at a synchronous power-balanced equilibrium, the direct derivatives with respect to inertia and damping vanish. If $M$ and $D$ also do not enter the algebraic equations, then $g_u=0$ and therefore $B_{u,r}=0$: algebraic elimination does not create first-order authority by itself. The package does not contain the actual ANDES DAE Jacobians or a finite-difference measurement, so whether the implemented Object A satisfies these conditions remains unresolved. The correct contribution is a conditional lemma plus an executable measurement recipe, not a claim that the channel is active or absent in the project plant.

### Hard facts

The environment interpolates the action-selected $M$ and $D$ values and writes them to `GENCLS` before each TDS substep [P3-S01]. Its diagnostic state derivative uses the package-source swing form

$$
\dot\omega_i=\frac{P_{m,i}-P_{e,i}-D_i(\omega_i-1)}{M_i}
$$

with a numerical denominator guard in code [P3-S02]. The imported theory audit states the reduced DAE channel $B_{u,r}=f_u-f_yg_y^{-1}g_u$ and explicitly records that the actual reduced/DAE Jacobians are not supplied [P3-S03]. These are package facts. No numerical value of $B_{u,r}$ is sealed.

### Assumption set

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

### Proposition P3.1 — index-1 Schur input channel

Under Assumptions 1–2, the locally reduced ODE obtained by eliminating $y$ has Jacobians

$$
A_r=f_x-f_y g_y^{-1}g_x,
\qquad
B_{u,r}=f_u-f_y g_y^{-1}g_u.
$$

#### Proof

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

### Proposition P3.2 — conditional zero first-order M/D authority

Under Assumptions 1–5, additionally suppose that:

- $M_i$ and $D_i$ enter no algebraic equation directly, so $g_u=0$ at the equilibrium; and
- $P_{m,i}$ and $P_{e,i}$ have no direct dependence on the $M/D$ command at fixed $(x,y)$.

Then the reduced first-order channel from the $M/D$ command is zero at the synchronous equilibrium:

$$
B_{u,r}=0.
$$

#### Proof

For each controlled swing row,

$$
\frac{\partial f_{\omega_i}}{\partial M_i}
=-\frac{P_{m,i}-P_{e,i}-D_i(\omega_i-\omega_s)}{M_i^2},
\qquad
\frac{\partial f_{\omega_i}}{\partial D_i}
=-\frac{\omega_i-\omega_s}{M_i}.
$$

Both derivatives vanish under Assumption 4. By the additional structural hypothesis, the remaining entries of $f_u$ vanish, and $g_u=0$. Proposition P3.1 then gives $B_{u,r}=0$.

### Exact routes by which $B_{u,r}$ can be nonzero

The proposition identifies the complete local routes:

1. **Direct differential route:** $f_u\ne0$. This occurs away from power balance, away from synchronous speed, when the action directly changes mechanical/electrical power, or when another differential row contains an additive action term.
2. **Algebraic Schur route:** $g_u\ne0$ and $f_yg_y^{-1}g_u\ne0$. This requires the action to enter algebraic power/current balance, a static converter relation, an active limiter equation, or another algebraic constitutive law. Merely having $f_y\ne0$ through electrical-power sensitivity is insufficient when $g_u=0$.
3. **Nonsmooth route:** an active-set change can produce a directional or generalized derivative even when the smooth-mode Jacobian is zero. That is a separate piecewise-smooth statement and must not be reported as the classical $B_{u,r}$.
4. **Gauge or singularity artifact:** using an unfixed angle gauge can make $g_y$ singular and the Schur expression undefined. A slack/reference condition or a projection to the balanced subspace is required before interpretation.

### Interpretation, kept separate from fact

The source structure makes a zero smooth channel plausible, because the action is written as $M/D$ parameters and the diagnostic swing derivative has the multiplicative form [P3-S01–P3-S02]. It is nevertheless not a measurement of the actual DAE Jacobian. In particular, the package does not expose the internal `GENCLS` algebraic residuals, network Jacobians, active-set derivatives, or the derivative of the feasibility-native action map. The correct current answer to “is $B_{u,r}$ nonzero for Object A?” is therefore **not identified from the shipped evidence**.

If Proposition P3.2 is verified, the local policy slope cannot create an additive first-order plant-state channel at the synchronous equilibrium through $M/D$ modulation; its leading effect is state-dependent/bilinear or higher order. If the finite-difference measurement instead finds a stable nonzero $B_{u,r}$ and the Schur reconstruction agrees, the project has identified the precise algebraic or direct route that completes the limitation in the ODE lemma.

### Finite-difference DAE verification plan

Let $e_j$ be one action coordinate and let $h$ be a decreasing perturbation magnitude (**HYPOTHETICAL numerical design**, to be registered against solver tolerance).

#### Direct reduced-channel measurement

For each $j$:

1. Freeze $x=x_\star$ and set $u_\pm=u_\star\pm he_j$.
2. Starting from $y_\star$, re-solve the algebraic equations $g(x_\star,y_\pm,u_\pm)=0$ with the same angle gauge and the same active mode.
3. Evaluate the differential residuals $f_\pm=f(x_\star,y_\pm,u_\pm)$ without advancing time.
4. Form
   $$
   \widehat B^{\mathrm{FD}}_{u,r}(:,j)=\frac{f_+-f_-}{2h}.
   $$
5. Repeat over a geometric $h$ sequence. A classical derivative is supported only if the estimate converges before solver noise dominates.

#### Independent Schur reconstruction

Measure $f_u,f_y,g_u,g_y$ by centered differences at the same equilibrium and form

$$
\widehat B^{\mathrm{Schur}}_{u,r}
=
\widehat f_u-
\widehat f_y\widehat g_y^{-1}\widehat g_u.
$$

Record the condition number and residual of the $g_y$ solves; never explicitly invert a poorly conditioned matrix. Compare $\widehat B^{\mathrm{FD}}_{u,r}$ with $\widehat B^{\mathrm{Schur}}_{u,r}$ column by column. Log action projection, saturation, limiter status, and algebraic active-set identity for every perturbation.

#### Decision rule

A nonzero smooth channel is supported when: (i) the centered derivative is stable over the registered $h$ range; (ii) it exceeds a preregistered numerical/noise bound; (iii) the Schur and direct estimates agree; and (iv) the active mode remains unchanged. It is refuted at the tested equilibrium when a registered upper confidence bound on every relevant entry or induced norm lies below the project’s materiality threshold. Both the numerical noise bound and materiality threshold are currently **HYPOTHETICAL** because no sealed values are provided.

### Reduced-model identifiability

Consider the deviation model

$$
\dot\theta=\omega,\qquad
M\dot\omega+D\omega+L\theta=B_w w+e.
$$

#### What is identifiable in principle

- With calibrated $w$, measured $(\theta,\omega,\dot\omega)$, known $M,D$, and persistently exciting probes, $L$ is identifiable on the angle-balanced subspace. The common angle is a gauge: $\theta$ and $\theta+c\mathbf 1$ are observationally equivalent when $L\mathbf 1=0$.
- Joint recovery of diagonal $M,D$ and $L$ is possible only if the stacked regressor has full column rank after imposing the gauge and structural constraints. Collinearity between $\dot\omega$, $\omega$, and $\theta$ destroys uniqueness.
- Symmetry $L=L^\top$, balance $L\mathbf 1=0$, and Laplacian sign structure are testable model restrictions, not facts to impose silently. Uncalibrated input scale creates an additional scaling ambiguity.

#### Residuals that should be reported

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

### Evidence binding

No experimental scalar is asserted for $B_{u,r}$ or the recovered $L$. The only implementation facts used are the package-source records [P3-S01–P3-S03]. All finite-difference step sizes, numerical tolerances, materiality thresholds, excitation amplitudes, and model-order choices are **HYPOTHETICAL** until registered and sealed.

### Missing quantity and minimal experiment

The package lacks the equilibrium residual vectors, $f_x,f_y,f_u,g_x,g_y,g_u$, algebraic conditioning, action-map derivative, active-mode log, and signed-probe trajectories with calibrated inputs. The minimal authority experiment is the equilibrium re-solve/centered-difference procedure above. The minimal identifiability experiment is a persistently exciting signed-probe record containing synchronized $w$, $\theta$, $\omega$, $\dot\omega$, operating-point metadata, and active-mode status, followed by constrained identification with held-out prediction.

### Paper-ready wording

For a continuously differentiable semi-explicit index-1 DAE $\dot x=f(x,y,u)$, $0=g(x,y,u)$ with nonsingular gauge-fixed $g_y$, algebraic elimination gives the exact reduced input Jacobian $B_{u,r}=f_u-f_yg_y^{-1}g_u$. For swing rows of the form $[P_m-P_e-D(\omega-\omega_s)]/M$, the direct derivatives with respect to $M$ and $D$ vanish at a synchronous power-balanced equilibrium. Hence, if the $M/D$ command does not enter the algebraic equations or any other differential residual directly, then $g_u=0$, $f_u=0$, and multiplicative $M/D$ feedback has no additive first-order reduced-state authority at that equilibrium. A nonzero first-order channel can arise only through direct action dependence, action-dependent algebraic balance, or a nonsmooth active-mode change. The present package confirms that the implementation updates live `GENCLS` $M/D$ parameters and uses the corresponding swing form [P3-S01–P3-S02], but it does not contain the actual ANDES Jacobians [P3-S03]. We therefore state the result conditionally and prescribe an equilibrium algebraic re-solve with centered finite differences, independently checked against the Schur reconstruction, before asserting whether the channel is active in Object A.
