# Q-0028 sealed-evaluation methodology audit (2026-07-24)

## Scope and bottom line

This note is an independent, methods-only audit for
[Q-0028](../../memory/questions/Q-0028.md). It does not select a controller,
inspect any Q-0028 trajectory, or modify the round state. The local protocol
already has the right experimental unit: `generate_test_scenarios` returns an
ordered, JSON-serializable scenario bank, and all controllers can be run on the
same bank
([generator source](../../src/andes_rl_kundur/evaluation/paper_strict_eval.py),
[generator tests](../../tests/test_paper_strict_eval.py)).

The proposed R265 design is methodologically usable with four qualifications:

1. Bootstrap **scenario rows jointly**, not controller columns independently.
   The confirmatory contrast should be the frozen R264 gate versus static
   alpha 0.25; R201 and droop are reference contrasts unless additional
   multiplicity rules are declared before unsealing.
2. `n=20` and 10,000 bootstrap replicates can describe uncertainty in mean
   paired effects, but there is no source-independent guarantee that 20
   scenarios have adequate coverage or power for these unknown response
   distributions. More resamples do not create more independent scenarios.
3. With 20 scenarios, empirical upper-tail CVaR at confidence 0.90 has only
   \(20(1-0.90)=2\) tail-observation equivalents. It should be a
   **descriptive guardrail**, reported with the two contributing losses and the
   maximum, not a strong tail-inference claim.
4. A seed is not a sealed bank. Persist the exact bank bytes and their SHA-256
   before evaluation, then record the generator provenance and serialization
   contract in a manifest.

These conclusions follow the primary statistical literature and official
implementations cited inline below. The numeric consequences for `n=20` are
arithmetic consequences of the predeclared design, not externally validated
sample-size claims.

## 1. Paired uncertainty on one sealed scenario bank

### Estimand and contrast

For endpoint \(m\), scenario \(i\), controller \(c\), let
\(Y_{icm}\) be a loss, so lower is better. Define the confirmatory paired
difference

\[
d_{im}=Y_{i,\text{gate},m}-Y_{i,\text{static-0.25},m}.
\]

The point estimate should be declared now, preferably the mean paired
difference \(\hat\Delta_m=n^{-1}\sum_i d_{im}\). A negative value favours the
gate. The median paired difference, interquartile range, and per-scenario
differences are useful robust/descriptive companions, but they must not replace
the declared estimand after results are seen. RL evaluations based only on
point estimates can be dominated by uncertainty or outliers; interval
estimates and distributional displays are recommended by Agarwal et al.'s
primary RL evaluation study
([NeurIPS paper](https://proceedings.neurips.cc/paper/2021/hash/f514cec81cb148559cf475e7426eed5e-Abstract.html),
[authors' source code](https://github.com/google-research/rliable)).

### Correct paired bootstrap

For each bootstrap replicate \(b=1,\ldots,B\):

1. draw one index vector \(I_b=(i_1,\ldots,i_n)\) with replacement from
   \(\{1,\ldots,n\}\);
2. use that **same** vector for every controller and endpoint;
3. recompute \(d_{im}\) and the complete statistic on the resampled rows.

This preserves the within-scenario controller pairing. Resampling each
controller independently discards the covariance created by common
disturbances and answers a different, less efficient question. SciPy's
first-party implementation exposes exactly this contract through
`bootstrap(..., paired=True)` and documents paired-sample statistics and
percentile/BCa intervals
([SciPy `bootstrap` documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html)).

Use \(B=10{,}000\), a separately fixed bootstrap RNG seed, and a two-sided 95%
percentile interval if that is the protocol chosen before unsealing. This is a
reproducible computational setting, but 10,000 resamples do not repair a weak
empirical distribution from only 20 scenarios. Efron's original BCa paper
explains why bias correction and acceleration can improve approximate
bootstrap intervals; SciPy also warns that percentile is the intuitive but not
generally preferred method
([Efron 1987](https://doi.org/10.1080/01621459.1987.10478410),
[SciPy interval methods](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html)).
For R265, keeping the already declared percentile method is preferable to
choosing BCa after looking at skewness; BCa can be reported only as a
predeclared sensitivity analysis.

### Co-primary endpoints and the decision rule

If `vsg_mean_iae` and physical normalized synchronization loss are genuinely
co-primary, success must require the predeclared criterion on **both**. This is
an intersection-union rule: declaring success only when every co-primary
endpoint succeeds does not introduce the same Type-I-error inflation as
allowing any endpoint to win, although it reduces power. An official FDA
multiple-endpoint guidance states this distinction explicitly and requires
prospective grouping and ordering of endpoints
([FDA 2022 guidance, section III.C.1](https://www.fda.gov/media/162416/download)).

R265 should therefore write one of these rules before any trajectory:

- **confirmatory positive:** both two-sided 95% paired intervals lie entirely
  below zero, and no hard guardrail fails;
- **directional/partial replication:** both point estimates are below zero but
  one or both intervals include zero, with no hard guardrail failure;
- **negative:** either co-primary point estimate is non-improving, or a hard
  failure/tail guardrail is violated.

The thresholds above are a project decision, not a universal statistical
standard. What is methodologically load-bearing is fixing the all-endpoint
rule, interval sidedness, and guardrails before unsealing. If success could be
declared from either endpoint, or from any of the six pairwise comparisons
among four controllers, a prospective multiplicity correction or ordered
testing scheme is required
([FDA multiple-endpoint guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/multiple-endpoints-clinical-trials)).

## 2. Small samples and failed trajectories

### What bootstrap can and cannot support

There is no universal theorem that makes `n=20` adequate for these endpoints;
adequacy depends on the target effect, variability, skew, failure mass, and
desired power. Agarwal et al. found in their own Atari experiments that
single-task bootstrap coverage close to 95% could require 20--30 runs, while
their stratified aggregate setting behaved differently. That result is a
warning against borrowing a generic sample-size number, not a power
calculation for Kundur disturbances
([Agarwal et al. paper and appendix](https://arxiv.org/abs/2108.13264)).
Bootstrap validity is not automatic for every statistic or data-generating
process; Bickel and Freedman's primary theoretical paper gives concrete
failure cases
([Bickel and Freedman 1981](https://doi.org/10.1214/aos/1176345637)).

With 20 scenarios, report all of the following for each co-primary endpoint:

- all 20 paired differences, or a machine-readable table that contains them;
- mean paired difference and the predeclared paired-bootstrap 95% interval;
- median, IQR, and min/max paired differences;
- count \(w=\#\{d_i<0\}\), with ties treated by a rule fixed before unsealing,
  and an exact binomial interval for the probability that the gate wins on a
  randomly drawn scenario.

The exact Clopper--Pearson construction remains defined at boundary counts
such as 0/20 or 20/20, where a Wald normal interval is especially misleading.
It is conservative, so label it “exact/conservative” rather than “most
powerful.” These properties are established in the original construction and
in Brown, Cai, and DasGupta's primary comparison study
([Clopper and Pearson 1934](https://doi.org/10.1093/biomet/26.4.404),
[Brown, Cai, and DasGupta 2001](https://doi.org/10.1214/ss/1009213286)).
As another distribution-free sensitivity summary, the continuous-i.i.d.,
no-tie interval \([d_{(6)},d_{(15)}]\) has 95.86% binomial coverage for the
population median when \(n=20\). If failures/censoring or ties violate that
construction, show the order statistics without calling it an exact interval
([NIST median confidence-limit method](https://www.itl.nist.gov/div898/software/dataplot/refman1/auxillar/mediancl.htm)).

### Failure is an outcome, not missing data

Never drop a controller-specific TDS failure and then bootstrap the remaining
values as if the deletion were independent. Predeclare:

- the exact failure predicate (`tds_failed`, incomplete horizon, non-finite
  endpoint, or protection/constraint crossing);
- per-controller failure count \(k/n\) and a two-sided 95% exact
  Clopper--Pearson interval;
- the paired \(2\times2\) table for gate/static outcomes:
  both complete, gate-only failure, static-only failure, both fail;
- an exact McNemar test or a matched-proportion interval if an inferential
  failure contrast is desired.

McNemar's original paper treats differences between correlated proportions,
which is the relevant pairing here
([McNemar 1947](https://doi.org/10.1007/BF02295996)). Exact confidence
intervals compatible with McNemar/sign tests are available, but are not the
same as two independent binomial intervals
([Fay and Lumbard 2021](https://pmc.ncbi.nlm.nih.gov/articles/PMC9447366/)).
For scale, observing 0 failures in 20 trials still gives a two-sided 95%
Clopper--Pearson upper limit of 16.84% (and a one-sided 95% upper limit of
13.91%); “20/20 completed” therefore does not establish a near-zero population
failure probability
([Clopper and Pearson 1934](https://doi.org/10.1093/biomet/26.4.404)).

For continuous physical endpoints, the safest R265 rule is hierarchical:
failure rate is a hard guardrail, and a continuous-endpoint analysis restricted
to scenarios where both controllers complete is explicitly labelled
“conditional on joint completion.” Such a conditional interval cannot rescue a
controller that failed more often. If the project instead needs one
failure-inclusive scalar, its finite penalty or engineering censoring limit
must be fixed before unsealing and applied identically to all controllers.

If a bootstrap distribution is degenerate, contains too few distinct values,
or produces a non-finite limit, report that fact, the point estimate, and the
raw paired values; do not silently switch interval method or delete failures.
The bootstrap approximates repeated sampling by resampling the empirical
distribution, so more replicates cannot reveal response values absent from the
original sample
([SciPy bootstrap algorithm](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html),
[Agarwal et al. discussion of few-run bootstrap](https://arxiv.org/abs/2108.13264)).

## 3. CVaR and worst-case guardrails

### Freeze the loss before freezing the tail statistic

CVaR applies to a scalar **loss**. For each guardrail, R265 must define before
unsealing:

- exact trajectory-to-loss map and units;
- direction (larger loss is worse);
- aggregation across buses and time;
- failure handling;
- confidence level \(q\);
- finite-sample estimator, quantile interpolation/tie convention, and interval
  method;
- which controller contrast and what constitutes a regression.

For upper-tail loss at \(q=0.90\), use the empirical
Rockafellar--Uryasev definition

\[
\widehat{\operatorname{CVaR}}_{0.90}(L)
=\min_z\left[
z+\frac{1}{n(1-0.90)}
\sum_{i=1}^{n}\max(L_i-z,0)
\right].
\]

This definition is preferable to an undocumented “average values above the
sample percentile” rule because it specifies the finite empirical
distribution and remains meaningful with discrete scenarios and ties.
Rockafellar and Uryasev developed CVaR for general, including discrete,
loss distributions and scenario samples
([author-hosted original paper](https://sites.math.washington.edu/~rtr/papers/rtr187-CVaR2.pdf),
[publisher DOI](https://doi.org/10.1016/S0378-4266(02)00271-6)).

The tail contrast itself must also be frozen. These answer different
questions:

- \(\operatorname{CVaR}(L_\text{gate})
  -\operatorname{CVaR}(L_\text{static})\): difference between controller-level
  tail risks;
- \(\operatorname{CVaR}(L_\text{gate}-L_\text{static})\): tail of the paired
  scenario deterioration;
- \(\max L_\text{gate}-\max L_\text{static}\): difference of bank maxima;
- \(\max_i(L_{i,\text{gate}}-L_{i,\text{static}})\): worst paired regression.

For the first and third contrasts, each bootstrap replicate must jointly
resample full scenario rows, recompute both nonlinear controller statistics,
and only then subtract. Computing all four and selecting the favourable one
after unsealing is outcome-dependent metric selection, not one confirmatory
tail analysis
([Rockafellar--Uryasev finite-scenario formulation](https://sites.math.washington.edu/~rtr/papers/rtr187-CVaR2.pdf),
[Nosek et al. on preregistration](https://doi.org/10.1073/pnas.1708274114)).

At `n=20`, CVaR90 has two tail-observation equivalents. Consequently, R265
should publish the maximum, the two largest losses, CVaR90, and the identities
of the contributing scenarios. A paired-bootstrap CVaR-difference interval may
be supplied as a sensitivity analysis, using joint scenario-row resampling,
but should not be described as precise tail evidence. The worst case is simply
the maximum over this sealed bank; it is bank-specific and has no general
population guarantee without additional distributional assumptions.

Do not choose `q`, endpoint, bus aggregation, or failure penalty after seeing
which option favours the gate. Preregistration is specifically the act of
defining research questions and the analysis plan before observing outcomes,
which separates confirmatory tests from exploratory findings
([Nosek et al. 2018](https://doi.org/10.1073/pnas.1708274114)). If CVaR90 is
too noisy after unsealing, report it as planned and label any CVaR80, trimmed
tail, alternative bus aggregation, or threshold study as exploratory. A better
prospective remedy is a larger bank, not post-result adjustment of \(q\).

## 4. Scenario-bank sealing and SHA-256

### Minimal artifact set

Before the first controller evaluation, save:

1. **Bank file:** the complete ordered scenario list, including explicit
   scenario IDs, in one immutable JSON file.
2. **Digest:** lowercase SHA-256 of the exact file bytes, plus file byte count.
   NIST FIPS 180-4 defines SHA-256 as a message-digest algorithm for detecting
   whether a message changed after its digest was generated
   ([NIST FIPS 180-4](https://doi.org/10.6028/NIST.FIPS.180-4)).
3. **Generation manifest:** `n`, scenario seed, `include_anchors=false`,
   generator import path, generator parameters and bounds, source commit,
   Python/NumPy versions, NumPy BitGenerator, platform, creation timestamp,
   bank filename, byte count, and SHA-256.
4. **Evaluation manifest:** controller labels, checkpoint/config digests,
   common environment seed/horizon, endpoint definitions, failure rule,
   confirmatory contrasts, bootstrap method/replicates/seed, CVaR definition,
   and decision gates.

Commit the bank and manifests before launching a controller and make every
result file repeat the bank SHA-256. Verify the digest immediately before each
controller batch and after the round. A changed digest invalidates the sealed
comparison; it is not repaired by editing the manifest.

SHA-256 alone proves only that the checked bytes match a recorded digest; it
does not prove when the digest was created. Put the bank digest and analysis
manifest into a versioned, timestamped record before the first trajectory. If
independent prospective-sealing evidence is required, use a registration
service that makes the submitted registration read-only; OSF's first-party
documentation describes registrations as timestamped, frozen versions that
cannot be edited after submission
([OSF registration documentation](https://help.osf.io/article/330-welcome-to-registrations)).

### Exact bytes and canonical JSON

SHA-256 hashes bytes, not abstract JSON objects. Two semantically identical
JSON serializations can have different bytes because of property order,
whitespace, number formatting, encoding, or line endings. Either retain the
exact bank file as the measurement of record or adopt a canonical
serialization. RFC 8785 specifies a hashable JSON representation using
deterministic property sorting, fixed primitive serialization, no insignificant
whitespace, and UTF-8; it also preserves array order
([RFC 8785 introduction and rules](https://www.rfc-editor.org/rfc/rfc8785.html)).

The minimum local contract can therefore be:

```text
schema = q0028-scenario-bank-v1
encoding = UTF-8, no BOM
serialization = RFC 8785 JCS
array_order = generator order, never sorted after generation
hash = SHA-256(canonical_file_bytes)
```

If no JCS implementation is used, document the exact serializer invocation and
still hash/preserve the materialized bytes. Do not claim that `seed=20260724`
alone is a durable seal. NumPy's official compatibility policy guarantees
`Generator` streams only under strict conditions involving the same
BitGenerator, calls, build, environment, and machine, and permits cautious
stream changes across feature releases
([NumPy RNG compatibility policy](https://numpy.org/doc/stable/reference/random/compatibility.html),
[NEP 19](https://numpy.org/neps/nep-0019-rng-policy.html)). This is why the
materialized bank, not regeneration from a seed, is the primary artifact.

## Recommended R265 pre-run contract

The following is a compact, auditable contract consistent with Q-0028:

| Item | Freeze before any trajectory |
|---|---|
| Bank | `n=20`, `scenario_seed=20260724`, `include_anchors=false`, persisted canonical JSON + SHA-256 |
| Primary contrast | R264 gate alpha-cap 0.25 minus static alpha 0.25 |
| Reference controllers | frozen R201 and droop k10; descriptive unless contrasts are explicitly added |
| Co-primary losses | exact formulas for `vsg_mean_iae` and physical normalized synchronization loss; lower is better |
| Pairing | common scenario row, environment seed, horizon, and failure predicate for all controllers |
| Main interval | mean paired difference, two-sided 95% percentile bootstrap, 10,000 joint row resamples, fixed bootstrap seed |
| Robust companion | raw paired deltas, median/IQR/min/max, win count with exact Clopper--Pearson interval |
| Failure | hard guardrail; exact per-controller interval + paired discordance table; no silent complete-case substitution |
| Tail | worst-bus and RoCoF upper-loss CVaR90 by the Rockafellar--Uryasev empirical formula; maximum + top-two losses shown |
| Tail interpretation | descriptive at `n=20`; paired bootstrap only as sensitivity, not strong tail inference |
| Action TV | exact aggregation and non-regression margin fixed now |
| Success | both co-primary criteria pass and no failure/tail/action-TV guardrail fails |
| Deviations | execute/report original plan first; any new alpha, endpoint, penalty, or aggregation is labelled exploratory |

The design is suitable for a **prospective mechanism-replication verdict**, but
`n=20` does not support a broad robustness or stable extreme-tail claim by
itself. The defensible result language is therefore “on this prospectively
sealed random bank, with paired uncertainty,” followed by the bank SHA-256 and
the raw failure/tail counts.

## Primary and official sources checked

- Agarwal et al., *Deep Reinforcement Learning at the Edge of the Statistical
  Precipice*: <https://arxiv.org/abs/2108.13264>
- Google Research `rliable` source: <https://github.com/google-research/rliable>
- SciPy paired bootstrap implementation documentation:
  <https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html>
- Efron, *Better Bootstrap Confidence Intervals*:
  <https://doi.org/10.1080/01621459.1987.10478410>
- Clopper and Pearson, exact binomial limits:
  <https://doi.org/10.1093/biomet/26.4.404>
- Brown, Cai, and DasGupta, binomial interval comparison:
  <https://doi.org/10.1214/ss/1009213286>
- Bickel and Freedman, bootstrap validity and failure cases:
  <https://doi.org/10.1214/aos/1176345637>
- NIST distribution-free median confidence limits:
  <https://www.itl.nist.gov/div898/software/dataplot/refman1/auxillar/mediancl.htm>
- McNemar, correlated proportions:
  <https://doi.org/10.1007/BF02295996>
- Fay and Lumbard, exact paired-proportion intervals:
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC9447366/>
- Rockafellar and Uryasev, CVaR for general loss distributions:
  <https://sites.math.washington.edu/~rtr/papers/rtr187-CVaR2.pdf>
- Nosek et al., preregistration:
  <https://doi.org/10.1073/pnas.1708274114>
- FDA, multiple endpoints and co-primary endpoints:
  <https://www.fda.gov/media/162416/download>
- NIST FIPS 180-4, SHA-256:
  <https://doi.org/10.6028/NIST.FIPS.180-4>
- OSF registration documentation:
  <https://help.osf.io/article/330-welcome-to-registrations>
- RFC 8785, JSON Canonicalization Scheme:
  <https://www.rfc-editor.org/rfc/rfc8785.html>
- NumPy RNG compatibility policy:
  <https://numpy.org/doc/stable/reference/random/compatibility.html>
