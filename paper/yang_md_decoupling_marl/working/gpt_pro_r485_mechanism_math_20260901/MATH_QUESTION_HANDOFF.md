# GPT Pro handoff — R485 finite-record mechanism audit

## Copyable request

You are receiving a build-only mathematical audit package for an ICEMS 2026
paper titled **“Decoupling-Oriented Coordination of Paralleled VSGs With
Multi-Agent Reinforcement Learning.”** Work only from the attached archive.

The paper's formal headline is already fixed: 121/208 all-fresh policies meet
both aggregate endpoints, but 0/208 pass the complete registered contract. Your
task is not to re-judge that result. Your task is to determine the strongest
mathematically defensible interpretation of the post-hoc TV/RMS mechanism
diagnostics.

Read in this order:

1. `MATH_PROBLEM_DRAFT.md` for the exact problem, implemented recursion,
   subgoals, terminal outcomes, and claim ceiling;
2. `DATA_GUIDE.md` and `DATA_DIGEST.md` for data identity and the compact
   observations;
3. `paper/PAPER_EVIDENCE.md` for the manuscript boundary;
4. the machine-readable result JSONs and probe/source code;
5. the representative checkpoint and four sealed trace JSONs if numerical
   differentiation or replay is useful.

Treat claims/feeds/formal result JSON as higher authority than prose. Treat
probe results as post-hoc finite-record evidence. The manuscript and this brief
are not scientific authority.

Please do all of the following:

1. Re-derive the metric and projector properties, including the difference
   between a one-step non-expansive map and a recursive stateful projector.
2. Determine whether the existing actual/fixed-prev/constant-anchor/projected
   comparisons admit an additive mechanism decomposition. If not, prove the
   non-identification and replace it with the sharpest valid bounds or declared
   allocation.
3. Derive a computable pathwise sensitivity certificate for the previous-action
   actor slots under the ReLU-`tanh` policy, handling kinks explicitly.
4. Audit the quasi-static RMS language, including the heterogeneous 24x4 grid
   and the different M/D prevalence.
5. Classify every conclusion as exact replay, finite-grid descriptive,
   actor-path intervention, or unidentified training/closed-loop claim.
6. Give the smallest manuscript-safe replacement: at most one displayed
   equation and at most 150 words of paper prose. If no mathematical
   strengthening is warranted, say `NO MATHEMATICAL CLAIM` and provide safer
   descriptive prose.

Do not infer plant counterfactuals from frozen observations. Do not call the
24 policies a random sample. Do not treat failure to pass the action guards as
hardware harm or safety evidence. Do not solve or revive Q-0112. Do not propose
new training or ANDES simulation.

If the full numerical certificate cannot be computed from the package, return
`DATA-UNDECIDABLE` for that subgoal and list the minimal missing tensors,
active-set records, checkpoint exports, or observation maps. Do not replace a
missing object with a convenient surrogate.

## Required return folder

Return exactly:

1. `SOLUTION.md` — proofs, dispositions, assumptions, and the minimal paper
   recommendation;
2. `verify_finite_record_certificate.py` — deterministic CPU-only replay or
   certificate checker for every new numerical statement;
3. `math_result.json` — machine-readable overall/subgoal dispositions, source
   locators, assumptions, values, and tolerances;
4. `manuscript_patch.tex` — at most one displayed equation and 150 words, or a
   comment containing `NO MATHEMATICAL CLAIM`;
5. `SHA256SUMS` — hashes of every returned file.

Do not edit supplied files. Do not return hidden reasoning or a generic
tutorial. Label every assumption, approximation, unverified theorem, and
non-identifiable quantity.

## Routing metadata

- Target consumer: GPT Pro conversational solver
- Interaction class: `none`
- Mathematical mode: `deep`
- Permission: `BUILD_ONLY`; the owner uploads the archive and decides whether
  to absorb the return
- Project-side acceptance: independent reconstruction and replay are required
  before any returned statement enters the paper
