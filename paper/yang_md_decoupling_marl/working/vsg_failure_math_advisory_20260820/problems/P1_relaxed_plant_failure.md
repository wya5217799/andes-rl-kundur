# P1 — Relaxed-plant failure block: what is and is not identified

**Type label: (P)**

## Headline result

The sealed evidence supports a paper-grade **ratio-sensitivity decomposition**, not a gain-margin or phase-margin diagnosis. The relaxed block fails because the fixed candidate achieves only a small reduction relative to that block's local reference; the package does not identify whether this comes from plant-loop sensitivity, movement of the local-reference denominator, or both. The channel-detuning explanation is separately refuted by R437.

## Hard facts

The constructive arm is `bandpass_k3p5` [P1-E01]. It records $r_d=0.9389467910702068$ and $r_{\mathrm{cross}}=0.5397906554502304$ in R408 [P1-E02–P1-E03], and $r_d=0.9382180713649944$ and $r_{\mathrm{cross}}=0.7937304481638234$ in the R409 held-out gate [P1-E04–P1-E05]. The R415 ceilings are $r_d\le 0.95$, $r_{\mathrm{cross}}\le 1.1$, with a strict cross ceiling of $0.95$ [P1-E06–P1-E08].

| R415 block | sealed $(M,D_i)$ | $r_d$ | local $E_d$ | candidate $E_d=r_dE_{d,L}$ | relative reduction $1-r_d$ | outcome |
|---|---:|---:|---:|---:|---:|---|
| conditions | $(200,100)$ [P1-E09–P1-E10] | 0.9322838738147555 [P1-E11] | 0.0005433139119660554 [P1-E13] | 0.0005065227985451632 [P1-D01] | 0.06771612618524447 [P1-D03] | pass [P1-E16] |
| relaxed | $(170,115)$ [P1-E17–P1-E18] | 0.9712251032133927 [P1-E19] | 0.00021018948180799598 [P1-E21] | 0.00020414130116334044 [P1-D04] | 0.028774896786607274 [P1-D06] | fail [P1-E24] |
| stiff | $(230,85)$ [P1-E25–P1-E26] | 0.907962726673478 [P1-E27] | 0.00030010287872978 [P1-E29] | 0.0002724822280540511 [P1-D07] | 0.092037273326522 [P1-D09] | pass [P1-E32] |

All three candidate guard bundles pass [P1-E15, P1-E23, P1-E31]. The three blocks do **not** use a matched disturbance/probe bank: their `condition_id` values differ under `results/research_loop/r415_energy_port_extra_banks/formal_analysis.json#/blocks/<block>/block/disturbance_conditions` and `#/probe_condition`. Consequently, differences across these rows are not finite differences with respect to $M$ or $D$.

R437 reports a relaxed-block peak at $0.44921875\,\mathrm{Hz}$ and a spectral-window fraction of $0.5866071101135871$ [P1-E34–P1-E35], versus passing-block peak frequencies $[0.33203125,0.390625]\,\mathrm{Hz}$ and window fractions $[0.5288535035245917,0.5034156773618179]$ [P1-E36–P1-E37]. Its registered mechanism verdict is `REFUTED` [P1-E38], with the stated reason that the relaxed spectrum remains inside the tested window in the same sense as the passing blocks [P1-E39].

## Assumption set

Let $\rho$ denote a scalar plant parameter or a differentiable path through $(M,D)$. Assume:

1. For a fixed disturbance/probe ensemble, the candidate and local-reference differential output maps $G_K(\mathrm{j}\omega;\rho)$ and $G_L(\mathrm{j}\omega;\rho)$ are differentiable in $\rho$.
2. The weighted energies $E_K(\rho)=\lVert G_K(\rho)\rVert_W^2$ and $E_L(\rho)=\lVert G_L(\rho)\rVert_W^2$ are positive, with the same nonnegative weighting operator $W$ and the same excitation ensemble.
3. The reported endpoint is $r_d(\rho)=E_K(\rho)/E_L(\rho)$.
4. The scalar-loop specialization below is used only when the measured candidate channel can be written as $G_K=P/(1+PK)$ with fixed $K$ and a well-posed loop.
5. The second-order swing transfer used later is **HYPOTHETICAL** until a reduced-model identification or Jacobian export is sealed.

## Proposition P1.1 — exact log-sensitivity decomposition

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

### Proof

Differentiate $r_d=E_K/E_L$ by the quotient rule. For $E(\rho)=\langle G(\rho),G(\rho)\rangle_W$, differentiability and Hermitian symmetry give $\partial_\rho E=2\operatorname{Re}\langle G,\partial_\rho G\rangle_W$. Dividing by $E_K$ and $E_L$ yields the log form. No control-specific approximation is used.

## Corollary P1.2 — fixed-controller scalar-loop contribution

Under Assumption 4, define $L=PK$ and $S=(1+L)^{-1}$. Then

$$
\partial_\rho\log G_K(\mathrm{j}\omega;\rho)
=S(\mathrm{j}\omega;\rho)\,\partial_\rho\log P(\mathrm{j}\omega;\rho).
$$

Thus the candidate-energy term in Proposition P1.1 is a weighted real projection of plant log-sensitivity through the **complex** sensitivity $S$; magnitude-only spectra do not determine it.

### Proof

From $G_K=P(1+PK)^{-1}$ with fixed $K$,

$$
\partial_\rho\log G_K
=\partial_\rho\log P-\frac{PK}{1+PK}\partial_\rho\log P
=\frac{1}{1+PK}\partial_\rho\log P.
$$

## HYPOTHETICAL reduced-swing specialization

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

## Interpretation, kept separate from fact

The sealed relaxed row is a **relative-performance** failure: its candidate differential energy is lower than the absolute candidate energies in the other two R415 rows [P1-D01, P1-D04, P1-D07], yet it is closer to its own local-reference energy and therefore exceeds the ratio ceiling. This does not prove that the local denominator caused the failure, because the disturbance/probe identities change with the block. It does prove that “the candidate's absolute differential energy became large” is not a valid description of the three-row table.

R437 removes one proposed explanation—coarse channel-frequency detuning within the registered spectral test—but it does not identify loop phase, gain crossover, Nyquist distance, or sensitivity peak. A PSD peak is not a stability-margin certificate.

## Evidence binding

All sealed and derived values used above are indexed in `evidence/evidence_register.csv`. The numerator reconstructions [P1-D01, P1-D04, P1-D07] are exact products of the corresponding sealed ratio and local energy. No value is back-filled across blocks. The swing transfer and its coefficients are explicitly marked **HYPOTHETICAL**.

## Verification plan

1. Re-run nominal, relaxed, and stiff $(M,D)$ settings on one **identical** signed disturbance/probe bank and one fixed simulation horizon. Preserve the same local-reference controller and normalization.
2. Export complex empirical frequency responses $G_K(\mathrm{j}\omega)$ and $G_L(\mathrm{j}\omega)$, not only PSD magnitudes. If the loop break is well-defined, also export $L(\mathrm{j}\omega)$.
3. Use central differences in $M$ and $D$ with a geometrically decreasing perturbation $h$ (**HYPOTHETICAL numerical design**) and verify convergence of both sides of Proposition P1.1.
4. Decompose the measured derivative into candidate and denominator terms. A candidate-loop mechanism is supported when the first term dominates reproducibly; a reference-normalization mechanism is supported when the second term dominates. Mixed dominance is admissible.
5. Compute phase margin or Nyquist distance only from a verified loop definition. Refute a claimed margin mechanism if the measured margin change has the wrong sign or cannot reproduce the endpoint derivative within uncertainty.

## Missing quantity and minimal experiment

The package lacks: (i) matched-block complex $G_K$ and $G_L$; (ii) a loop-broken complex $L$; (iii) matched finite differences in $M$ and $D$; and (iv) uncertainty estimates. The minimal experiment is a matched nominal/relaxed/stiff small-amplitude signed-probe sweep with complex response estimation for both the candidate and local reference. Without it, a margin-level causal explanation is not solvable from the shipped data.

## Paper-ready wording

For the fixed `bandpass_k3p5` controller, the relaxed R415 block is rigorously characterized as a relative-energy failure rather than an identified stability-margin failure. Writing the registered differential endpoint as $r_d=E_K/E_L$, where $E_K$ and $E_L$ are candidate and local-reference energies under a common excitation and weighting, gives the exact sensitivity identity $\partial_\rho\log r_d=2\operatorname{Re}\langle G_K,\partial_\rho G_K\rangle_W/\lVert G_K\rVert_W^2-2\operatorname{Re}\langle G_L,\partial_\rho G_L\rangle_W/\lVert G_L\rVert_W^2$. In the sealed relaxed block, $r_d=0.9712251032133927$ [P1-E19], while the reconstructed candidate and local energies are $0.00020414130116334044$ and $0.00021018948180799598\,\mathrm{Hz}^2\mathrm{s}$ [P1-D04, P1-E21], respectively; hence the controller supplies only a $0.028774896786607274$ relative reduction [P1-D06], below that required by the registered $0.95$ ceiling [P1-E06]. R437 separately refutes the registered spectral-detuning explanation [P1-E38]. Because the R415 blocks use different disturbance and probe identities and the package contains no complex loop response, these results do not identify an $M$/$D$ derivative, gain margin, phase margin, or universal robustness boundary; those require a matched complex-response finite-difference experiment.
