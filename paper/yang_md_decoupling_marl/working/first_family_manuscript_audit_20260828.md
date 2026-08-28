# First-family manuscript audit — 2026-08-28

## Scope

- Writing family: `tech-paper-template` plus `intro-drafter`.
- Manuscript: `Decoupling-Oriented Coordination of Paralleled  VSGs With Multi-Agent Reinforcement Learning`.
- Evidence admitted for scientific claims: R478, R480, R481, R483, and R484 only, with the registered parameter card and the paper evidence map.
- No ANDES run, training, evaluation, tuning, or new experiment was performed during rewriting or review.
- The working tree was preserved. Review freezes use exact file hashes; no Git commit or staging operation was created.

## Rewrite outcome

The prior positive controller narrative was replaced by a bounded audit paper. The rewritten argument separates:

1. the R481 deterministic fresh-bank feasibility result;
2. the R483 learned source-factorial result at 6 s;
3. the R484 learned canary-bank guard audit and 30 s sensitivity;
4. the R480 open-loop horizon warning; and
5. the R478 device/system-base correction.

The manuscript does not pool fresh with canary profiles, deterministic with learned policies, or 6 s with 30 s. It does not claim cross-topology, cross-inertia, stability, safety, EMT/HIL, deployment, population failure probability, or universal MARL failure.

## First review and repairs

The first scientific, language, and format passes found no need for new experiments. They did find manuscript-definition and package-scope defects, which were closed as follows:

- corrected the learner description to four independent per-VSG SAC learners, without parameter sharing or a joint critic;
- specified the amplitude/slew projection before decoding, lower clamps, device-to-system conversion, and five runtime-readback interpolation substeps;
- defined the direct-law 60/50 observation adapter, dimensionless features, candidate eligibility, lexicographic selection directions, and tie-break;
- specified the frozen same-time circular placebo-donor mapping;
- expanded the training reward, replay/update recipe, adaptive-stop certificate, inferential unit, exact Wilcoxon validity route, sign-flip fallback, and Holm family;
- separated direct-law, MARL-state, and reward-frequency symbols;
- defined endpoint normalization magnitudes and the parameter-card anchor/profile overrides;
- mapped all four Introduction contributions to their manuscript sections;
- removed ambiguous language around deterministic versus learned guard sets, per-profile guard failure, and `direct-M/D` terminology;
- kept the paper at six IEEE conference pages with no overfull box, undefined citation, or undefined reference.

Historical figures and the superseded supplement remain preserved in the repository. They are excluded from the current submission package through an exact allowlist rather than deletion.

## Final first-family closure

Final review freeze:

- `manuscript/main.tex`: `A19922C9B3E330FEC5ABE682A9737A108B5ABA2782563898C7453589B2EE9277`
- `manuscript/main.pdf`: `8E77E376EF8D81B0DFC8AE2305A77E6FE398E51251641515EEA064767284CA1D`

Three role-separated closure reviews returned:

- scientific correctness: 0 CRITICAL, 0 MAJOR, PASS;
- language/argument and `intro-drafter` hard checks: 0 CRITICAL, 0 MAJOR, PASS;
- format/rendering: PASS; six A4 IEEE pages, readable equations/tables/figures, embedded subset fonts, no Type 3 fonts, and no visible clipping or overlap.

Residual non-blocking log output consists of underfull boxes and one `balance` warning without a visible layout defect.

## Experiment decision

No additional experiment is required for the paper's present finite-bank negative/trade-off thesis. New prospective experiments would be required only if the manuscript were expanded to claim learned-policy performance on the fresh bank, robustness across topology or inertia, a stability/safety certificate, EMT/HIL validity, or deployment performance.

## Post-freeze layout note

This first-family format PASS did not test semantic float order. It therefore missed that the claim-bearing two-column result figure could float after the Conclusion while remaining unclipped and legible. The final manuscript later corrected that ordering and added explicit gates requiring each figure to be cited before it appears and every body figure to precede the Conclusion; the historical hashes above remain the actual first-family review freeze.
