# Source Verification Report

## Overall assessment

- Scope: all U1--U9 claims in `01_complete_solution.md`, the paper-ready wording,
  source map, and machine checks.
- Authority: the imported GPT Pro text is a design aid. Sealed repository results,
  current code, prospective plans, sidecars, and locally reproduced algebra outrank it.
- Package integrity: the original 1,554-entry evidence pack re-hashes with zero
  failure; the imported answer's 10 declared files also re-hash with zero failure.
- Reproduction: bundled blueprint tests pass. Re-running `verify_solution.py` changes
  only `source_root` and one Clopper--Pearson last-bit value (`1e-18` scale).
- Independent check: `verification/repo_checks.json`
  verifies the U1 dimension, U2 placebo combinatorics, U3 repository projector,
  U4 bounds, U5 MIMO derivative, U6 ZOH split, U8 identities, and U9 branch table.

## Source quality matrix

| Source | Evidence role | Currency | Conflict / limitation | Grade |
|---|---|---|---|---|
| R446--R458 formal JSON and sidecars | Primary project evidence | current | finite declared banks only | A |
| Sealed plans and current source code | prospective contract and implementation semantics | current | code does not itself prove physical outcomes | A |
| Independent repo check JSON | algebraic/numerical replication | current | plant-agnostic for U1/U5/U6/U7/U8 | A- |
| GPT Pro complete solution | external mathematical analysis | current | self-authored checker; conditional propositions mixed with outcomes | B-/C+ |
| Paper-ready wording | derivative prose | current | cannot outrank proofs or sealed outcomes | C |

## Per-claim verdicts

| Item | Verification verdict | Reason |
|---|---|---|
| U1 | VERIFIED as a non-identifiability boundary | The pack lacks Object-B sampled I/O arrays, verified DCF/SLS lifts, active-mode tube, and primal/dual data. The proposed 10-tap/90-parameter class is new design input, not a sealed project class. |
| U2 | QUALIFIED | The 3x3x2 design and pooled-marginal placebo combinatorics are valid. Population intrinsic information value and any outcome remain unverified; the current line does not authorize this training experiment. |
| U3 | VERIFIED | The repository implementation includes previous executed action, stores executed action, and projects target/actor actions consistently. The alias counterexample is exact; no numerical Bellman-bias magnitude is available. |
| U4 | QUALIFIED | Non-inclusion of an expected common quadratic constraint in the full profile-wise guard set is proved. The `0.0009421117` bound is a conservative common-only sufficient bound under a per-record undiscounted-budget assumption, not a recommended budget or full-feasibility threshold. |
| U5 | VERIFIED as a generic identity | Independent random-MIMO centered difference matches the total derivative at relative error `6.88e-10`. No Object-B total derivative, margin, or causal channel attribution is computed. |
| U6 | VERIFIED with explicit assumptions | The exact ZOH split and the conditional 0--0.2 s endpoint bracket are valid. The 0.19508 s interpolation is descriptive only; no pole-crossing or robust-stability margin is identified. |
| U7 | MAJOR QUALIFICATION REQUIRED | `f_u(0)=0` alone does not imply a bilinear leading term: `f(u)=u^2` is a counterexample. The proposition also needs equilibrium invariance for every nearby M/D command in one smooth mode (hence pure-action derivatives vanish), or it must include pure `u^2` terms. The supplied paper-ready paragraph is not accepted verbatim. |
| U8 | VERIFIED as a conditional structural result | The commutator identity and projector heterogeneity identity reproduce. Numerical DAE/cross-energy bounds remain unavailable without reduced I/O matrices and conditioning factors. |
| U9 | VERIFIED and empirically instantiated | R458 selected priority 1 without evaluation access and returned `GUARD-CLEAN-TRANSFER` on 2 of 4 fixed evaluation profiles. The count is descriptive, not binomial probability evidence. |

## Flagged-source details

1. **Major -- resolution overstatement**: README says U2--U9 are resolved. Project
   disposition is narrower: U2 is a future causal design, U7 needs an extra
   assumption, U8 is structural rather than numerical, and U9 required R458 outcome.
2. **Major -- U7 omitted term/assumption**: the generic reduced Taylor model omits
   `f_uu[u,u]/2`. Repair by adding nearby-command equilibrium invariance or retaining
   the pure-action quadratic term.
3. **Minor -- U4 numerical interpretation**: preserve the strong per-record and
   common-only qualifications; never use the bound as a complete guard threshold.
4. **Minor -- U9 hypothetical intervals**: Clopper--Pearson values are mathematically
   correct under an added IID model but are unauthorized for the four fixed profiles.

Predatory-journal, author-identity, citation-existence, and financial-COI checks are
not applicable: the package cites repository artifacts rather than publications.

## Decision

**CONDITIONAL PASS.** The package is authentic and highly useful, but only the
bounded dispositions above may enter project reasoning. U7 paper wording is blocked
until corrected; U2 outcomes, U1 feasibility, numerical U5/U6/U7/U8 results, transfer
probability, topology generalization, stability, and safety remain unverified.
