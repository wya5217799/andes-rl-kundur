# P2 — Discrete controller-delay boundary

**Type label: (P)**

## Headline result

A pure integer delay admits an exact phase-loss and sensitivity-amplification formula. The sealed R440 data establish only that the tested one-step and two-step implementations violate the differential endpoint while retaining the registered guards. They do not provide the complex nominal loop, crossover frequency, or a same-bank zero-delay case, so neither an analytic time-delay margin nor a causal phase-margin explanation can be numerically identified from the package.

## Hard facts

The differential ceiling is $0.95$ [P1-E06]. R440 records:

| delay | $r_d$ | excess above ceiling | $r_{\mathrm{cross}}$ | candidate/local $E_d$ | guards | unit outcome |
|---:|---:|---:|---:|---:|---|---|
| 1 step [P2-E01] | 0.9502787849106537 [P2-E02] | 0.0002787849106536955 [P2-D01] | 0.6055328645068879 [P2-E03] | 0.00039037026048215306 / 0.0004107955125177883 [P2-E06–P2-E07] | pass [P2-E04] | fail [P2-E05] |
| 2 steps [P2-E10] | 0.9893270595363578 [P2-E11] | 0.039327059536357845 [P2-D02] | 0.6405191344833928 [P2-E12] | 0.0004438716827728703 / 0.0004486602064446596 [P2-E15–P2-E16] | pass [P2-E13] | fail [P2-E14] |

The overall registered verdict is `BOUNDED-FAILURE` [P2-E19]. The physical duration represented by one step is not a sealed scalar in the R440 JSON files; any conversion from steps to seconds in this report would therefore be **HYPOTHETICAL** under the intake contract.

## Assumption set

Assume:

1. A scalar, well-posed, discrete-time negative-feedback loop has nominal complex loop transfer $L_0(e^{\mathrm{j}\Omega})$.
2. An integer computational delay of $n$ samples enters only as the multiplicative factor $e^{-\mathrm{j}n\Omega}$ in that loop; plant, controller coefficients, sampling, excitation, and endpoint denominator are otherwise unchanged.
3. The output channel of interest has a numerator unaffected by the delay, so its delay dependence is carried by the sensitivity denominator.
4. For the phase-margin corollary, a regular unit-gain crossover $\Omega_c$ and a locally dominant crossover exist. This is a local statement, not a global Nyquist certificate.
5. Converting sample delay to physical time requires a verified sample period; no numerical period is assumed here.

## Proposition P2.1 — exact integer-delay sensitivity ratio

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

### Proof

Substitute the delayed loop into the sensitivity definition, take the squared modulus, and use $|1+\ell e^{\mathrm{j}\psi}|^2=1+\ell^2+2\ell\cos\psi$.

## Corollary P2.2 — infinitesimal delay direction

For a continuous delay parameter $\tau$ in $L_\tau(\mathrm{j}\omega)=L_0(\mathrm{j}\omega)e^{-\mathrm{j}\omega\tau}$,

$$
\frac{\partial}{\partial\tau}\log|S_\tau(\mathrm{j}\omega)|^2
=
-\frac{2\ell\omega\sin(\phi-\omega\tau)}
{1+\ell^2+2\ell\cos(\phi-\omega\tau)}.
$$

The sign is frequency- and phase-dependent. Delay is therefore not guaranteed to increase every weighted output energy monotonically, even though it reduces phase at each positive frequency.

## Corollary P2.3 — local phase-margin loss at a regular crossover

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

## Endpoint-level consequence

For a fixed excitation weighting $W$ and a fixed local-reference denominator $E_L$, the delayed differential endpoint can be written

$$
r_d(n)=\frac{\lVert N S_n\rVert_W^2}{E_L}.
$$

Proposition P2.1 therefore converts a measured complex loop $L_0$ into a predicted endpoint curve. Without $L_0$, only the two sealed endpoint samples are known. In particular, comparing R440 to R408 would mix experiment banks and cannot supply the missing zero-delay value for this curve.

## Interpretation, kept separate from fact

The one-step result is a narrowly missed endpoint, not evidence of instability: the differential ratio exceeds the ceiling by the sealed amount [P2-D01] while all registered guards pass [P2-E04]. The two-step case moves farther above the ceiling [P2-D02], which is directionally consistent with phase loss but does not establish phase loss as the causal mechanism. The cross endpoint remains below its strict ceiling in both cases [P2-E03, P2-E12, P1-E08], so the observed boundary is differential-channel specific within this test.

## Evidence binding

All numerical statements are linked to `evidence/evidence_register.csv`. The excess values [P2-D01–P2-D02] are exact subtractions from the sealed $0.95$ ceiling. No zero-delay value, sample period, gain crossover, phase margin, or loop transfer is inferred. Any future physical-time conversion is **HYPOTHETICAL** until its timing field is sealed.

## Verification plan

1. Add a same-bank zero-delay record with the identical disturbances, probes, local reference, horizon, and endpoint code used by `delay_1.json` and `delay_2.json`.
2. Record the exact control sample period and the location of the delay in the signal path.
3. Break or identify the loop and export $L_0(e^{\mathrm{j}\Omega})$ as a complex array over the endpoint-relevant band.
4. Compute $S_n$ from Proposition P2.1 for each tested integer $n$, propagate it through the measured numerator, and predict $r_d(n)$ with no fitted phase offset.
5. Support the phase-loss mechanism if the predicted endpoint curve and measured same-bank curve agree within registered uncertainty and the inferred crossover phase decreases by $n\Omega_c$. Refute it if the complex-loop prediction has the wrong endpoint direction or cannot explain the measured change.
6. Report separately: endpoint boundary, local phase-margin boundary, and nonlinear/guard boundary. Do not substitute one for another.

## Missing quantity and minimal experiment

The missing quantities are the same-bank $n=0$ endpoint, the exact sample period, the complex nominal loop $L_0$, the output numerator/weighting map, and uncertainty across repeated runs. The minimal experiment is a registered integer-delay sweep including zero delay, accompanied by one complex loop-identification export. Without those quantities, the package supports an exact symbolic delay law and two bounded failure observations, but no numerical analytic delay margin.

## Paper-ready wording

For a fixed discrete-time feedback loop with nominal complex loop transfer $L_0(e^{\mathrm{j}\Omega})$, an integer delay of $n$ samples changes the sensitivity exactly to $S_n=(1+L_0e^{-\mathrm{j}n\Omega})^{-1}$, giving $|S_n/S_0|^2=(1+\ell^2+2\ell\cos\phi)/(1+\ell^2+2\ell\cos(\phi-n\Omega))$ for $L_0=\ell e^{\mathrm{j}\phi}$. At a regular unit-gain crossover, this corresponds locally to the phase-margin loss $\mathrm{PM}_n=\mathrm{PM}_0-n\Omega_c$; however, the registered energy endpoint may fail before any stability boundary is reached. In R440, the one-step and two-step cases yield $r_d=0.9502787849106537$ and $0.9893270595363578$ [P2-E02, P2-E11], respectively, both above the registered $0.95$ ceiling [P1-E06], while their no-harm guards remain satisfied [P2-E04, P2-E13]. These observations establish a bounded controller-delay failure of the differential endpoint, not an instability claim. Because the sealed files omit a same-bank zero-delay case, the physical sample period, and the complex loop response, they do not identify a numerical delay margin or prove that phase loss is the sole mechanism; those claims require the registered complex-response delay sweep specified here.
