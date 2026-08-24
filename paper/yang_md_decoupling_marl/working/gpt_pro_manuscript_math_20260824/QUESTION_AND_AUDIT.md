# GPT Pro brief: bounded mathematical strengthening of the ICEMS manuscript

## Identity and decision context

- Manuscript title: **Decoupling-Oriented Coordination of Paralleled VSGs With Multi-Agent Reinforcement Learning**.
- Target: ICEMS 2026, five-page IEEE conference manuscript.
- Date of this package: 2026-08-24.
- Scope: mathematical audit and minimal paper strengthening from already sealed evidence. Do not run ANDES, train a controller, tune a learner, invent missing signals, or change any sealed result.
- Current writing decision: the mathematics is sufficient for the bounded conference paper. The external answer is an optional strengthening pass, not a submission or drafting gate.

Use the files in this archive only. A proof or numerical statement must cite an archive path and, for JSON/NPZ data, the exact field or array. If the supplied material does not identify a requested object, return `DATA-UNDECIDABLE` and name the minimal missing objects. Do not replace an unidentifiable quantity with a convenient surrogate.

## Evidence authority

When files disagree, use this precedence:

1. final formal guards and hashed decision artifacts;
2. current claim cards;
3. canonical feed reports;
4. sealed result arrays, manifests, traces, and source code;
5. manuscript prose and prior external-solver text.

The manuscript is an object to audit, not evidence authority. External theory is advisory until its algebra, assumptions, project-side replay, and model gap are all verified.

## What mathematics the manuscript currently uses

The paper already defines:

1. the asymmetric normalized-action decoder

   \[
   \Delta q(a)=\begin{cases}600a,&a\ge 0,\\200a,&a<0,\end{cases}
   \qquad q\in\{M,D\};
   \]

2. the arithmetic common coordinate and a fixed differential basis

   \[
   z_c=\mathbf 1^\top\Delta f/4,\qquad
   z_d=T_d\Delta f,
   \]

   \[
   T_d=\begin{bmatrix}
   1/2&1/2&-1/2&-1/2\\
   1/\sqrt2&-1/\sqrt2&0&0\\
   0&0&1/\sqrt2&-1/\sqrt2
   \end{bmatrix};
   \]

3. the index-1 DAE folded input channel at the synchronous power-balanced equilibrium

   \[
   B_{u,r}=f_u-f_y g_y^{-1}g_u=0;
   \]

4. a row-permuted neighbour-source intervention and a paired six-seed materiality analysis.

The paper intentionally does not include the previous P1/P2 loop-margin formulae, the Object-B QY10 conic certificate, generic commutator/Schur bounds, or a universal M/D impossibility theorem. Those results address unmatched control objects, missing project quantities, or a scope too large for the five-page paper. Their omission is not, by itself, a mathematical gap.

## Sealed facts relevant to this audit

### F1. Equilibrium first-order M/D authority

For Object A (four GENCLS VSG proxies), the R446 finite-difference Schur fold uses eight physical parameter columns, \(\{\Delta M_i,\Delta D_i\}_{i=1}^4\), and step sizes \(10^{-2},10^{-3},10^{-4}\). At the nominal synchronous equilibrium:

- all four VSG speeds are exactly 1.0 p.u.;
- \(\max|f_\omega|=1.54\times10^{-10}\), \(\max|f|=7.23\times10^{-9}\), and \(\max|g|=2.91\times10^{-9}\);
- \(\operatorname{cond}(g_y)=1.14\times10^6\);
- every folded column has \(\max|B_{u,r}[:,j]|=0\) at every registered step size.

The allowed conclusion is equilibrium-only: direct M/D modulation has no additive first-order reduced-state channel at balance. It does not say M/D has no transient effect and does not identify the sole cause of learning failure.

### F2. Local order and nonsmooth interface

R468 exports converged physical-parameter tensors on the fixed-mode, gauge-reduced, 101-state sampled model:

\[
N=\partial A_d/\partial q\in\mathbb R^{8\times101\times101},\quad
E=\partial B_d/\partial q\in\mathbb R^{8\times101\times7},
\]

\[
R=\partial C_d/\partial q\in\mathbb R^{8\times4\times101},\quad
S=\partial D_d/\partial q\in\mathbb R^{8\times4\times7}.
\]

The largest Richardson relative difference is \(1.88\times10^{-5}\); exact-ZOH Frechet checks agree within \(3.34\times10^{-7}\) relative. On the sealed nonlinear amplitude ladder, all 12 blocks are empirically quadratic-leading under the registered last-two-level test. A separate additive energy-port lift is nonzero and first-order on the sampled model.

However, the implemented normalized controller/decoder is nonsmooth at zero: the observation derivatives differ by as much as 8 and the decoder slopes are 200 and 600 on opposite sides. Therefore no single smooth normalized-policy Taylor theorem is authorized. The complete bilinear lift is an open pseudo-input map, not a policy-specific closed-loop Volterra kernel.

### F3. Clean neighbour-source factorial

For each seed \(s\in\{401,\ldots,406\}\), actor source \(a\in\{N,P\}\), critic source \(c\in\{N,P\}\), and reward-access factor \(r\in\{0,1\}\), let \(Y_{sacr}>0\) be the registered upper-median held-out disturbance-differential energy.

The authentic source \(N\) uses each recipient's same-time ring-neighbour tuple. The placebo retains recipient-local columns 0:3 and applies the fixed-point-free row permutation \(\rho(i)=(i+1)\bmod4\) only to the four neighbour columns:

\[
P[i,3{:}7]=N[\rho(i),3{:}7].
\]

At every time, the four-value multiset of each neighbour column and the multiset of the four ordered neighbour tuples are unchanged globally, but recipient-to-neighbour alignment is changed.

Define the per-seed actor and critic contrasts as

\[
d_s^A=\frac14\sum_{c\in\{N,P\}}\sum_{r\in\{0,1\}}
\left[\log Y_{sPcr}-\log Y_{sNcr}\right],
\]

\[
d_s^C=\frac14\sum_{a\in\{N,P\}}\sum_{r\in\{0,1\}}
\left[\log Y_{saPr}-\log Y_{saNr}\right].
\]

Positive values favour the authentic source. R477 reports:

- actor: \(\bar d^A=-0.0248\), geometric effect \(-2.45\%\), descriptive bootstrap interval \([-0.0882,0.0450]\), one of six seed effects positive;
- critic: \(\bar d^C=0.0442\), geometric effect \(+4.52\%\), descriptive bootstrap interval \([-0.0092,0.0908]\), five of six seed effects positive;
- materiality threshold \(\delta=\log(1.10)\);
- direct one-sided materiality p-values 0.984375 and 0.953125 from all \(2^6\) sign assignments, followed by Holm correction over actor and critic;
- neither factor establishes an effect above the 10% bar;
- with six seeds, power at a true 20% effect is about 73.5%, so this is not an equivalence or zero-effect result.

The intervention identifies only the total algorithmic effect of authentic same-time recipient-aligned sources versus the row-permuted source. It does not isolate a pure semantic neighbour-information value.

### F4. Still-open information-margin question

The registered Q-0112 asks whether a finite-bank non-anticipative information-level margin program can certify or refute `INFORMATION-LIMITED` for the 2% joint target under the exact R352/R353 histories. R445 already shows that the zero-sum edge action basis is insufficient in 6/16 scenarios, while bases containing the fleet-equal direction reach the target. It does not supply an endogenous action-dependent observation tree, and the information ownership of the common \(B_+\) coordinate is not declared.

R477 does not close Q-0112. Its row-permuted source contrast uses a different learned-control object and does not identify the exact dynamic non-anticipative classes required by Q-0112. Q-0112 is a successor-line mathematical problem, not a condition for submitting the current ICEMS paper.

## Task A — audit the current manuscript's DAE/local-order statement

1. Re-derive the index-1 reduction for

   \[
   \dot x=f(x,y,q,w),\qquad 0=g(x,y,q,w),
   \]

   with gauge-fixed nonsingular \(g_y\), and state exactly when

   \[
   B_{q,r}=f_q-f_y g_y^{-1}g_q
   \]

   vanishes at a synchronous power-balanced equilibrium.
2. Starting from F1 and F2, determine the strongest correct local-order statement for the implemented piecewise controller and asymmetric decoder. Distinguish:
   - zero additive first-order equilibrium channel;
   - mixed state/parameter terms;
   - possible pure \(q^2\) terms;
   - one-sided or piecewise expansions;
   - the sealed finite-ladder empirical result.
3. Audit this current manuscript sentence:

   > Direct M/D modulation has zero folded first-order input authority at the balanced equilibrium, whereas its influence becomes state dependent during transients. This is consistent with a difficult residual-learning interface.

   State `PASS`, `QUALIFY`, or `FAIL`, with a precise reason.
4. Decide whether the paper should add a compact lemma, replace one sentence, or leave the mathematics unchanged. The preferred output is the smallest defensible change that fits a five-page IEEE conference paper. Do not propose a long theory section merely because more mathematics exists.
5. Provide camera-ready LaTeX for at most one displayed equation and at most 130 words of explanatory prose. Every clause must be bounded to the tested equilibrium, fixed mode/window, and piecewise implementation as applicable.

## Task B — audit the source estimand and exact materiality inference

1. Prove exactly which global time-slice multisets the row permutation preserves and which recipient-conditional/joint structures it changes. State whether this is enough to call the design a placebo, and define the treatment contrast it actually identifies.
2. Using the supplied R477 raw evaluation JSONs and runner, independently reconstruct \(d_s^A\), \(d_s^C\), the two mean log effects, geometric effects, sign counts, descriptive bootstrap intervals, materiality p-values, and Holm decisions.
3. Audit the exact test. State the exchangeability or symmetry assumption needed when sign-flipping \(d_s-\delta\) for \(H_0:\mu_d\le\delta\), whether the code implements the claimed test, and the attainable p-value resolution at \(n=6\). Do not convert failure to reject into equivalence.
4. Give one manuscript-safe estimand sentence and one stay-out sentence. In particular, say whether `pure semantic neighbour-information value` is identified. If it is not, return `PURE-SEMANTIC-EFFECT-NOT-IDENTIFIED` and give the minimal additional interventions or assumptions required for identification. This is a design answer only; it does not authorize new training.

## Task C — dispose of Q-0112 without contaminating the current paper

1. Audit whether the supplied R352/R353 histories, R445 matrices, and action/constraint code identify:
   - an exact endogenous non-anticipative information tree under arbitrary action prefixes;
   - only a frozen-log diagnostic partition;
   - a declared measurement-error/Lipschitz relaxation;
   - a valid owner and observation map for the fleet-common coordinate in \(B_+\).
2. If the exact tree and common-channel ownership are identified, formulate and solve the finite-bank shared-action max-margin program and return a replayable certificate.
3. If either is not identified, return `DATA-UNDECIDABLE`, prove the non-identification from the archive, and list the minimal state transition, observation, ownership, and uncertainty maps required. Do not treat the absence of identical floating-point logged histories as evidence of information sufficiency.
4. State explicitly that Task C is either future work or a successor-line result and cannot raise the current manuscript's claim ceiling without a separately governed evidence intake.

## Required return folder

Return exactly these files:

1. `SOLUTION.md`: proofs, numerical reconstruction, dispositions, and minimal manuscript recommendation;
2. `manuscript_patch.tex`: only the proposed replacement/addition, or a comment saying `NO CHANGE`;
3. `verify_manuscript_math.py`: deterministic CPU-only replay for every numerical claim made from the package;
4. `math_audit_result.json`: machine-readable task dispositions, assumptions, source paths/locators, recomputed values, and tolerances;
5. `SHA256SUMS`: hashes of all returned files.

Do not edit the supplied manuscript. Do not return hidden reasoning or a generic tutorial. Label every new assumption, approximation, and unverified theorem.

## Claim ceiling

Even a successful answer is limited to the named equilibrium, fixed-mode local models, sealed finite windows/banks, six seeds, the tested learner/projector, and the stated placebo. It cannot establish universal MARL value, universal communication value, topology generalization, nonlinear/global stability, safety, deployment readiness, controller-class impossibility, or a pure semantic information effect without the missing intervention or information-tree evidence.
