# R485 GPT Pro action-guard answer: project-side intake review

## Disposition

`ACCEPT-AS-CLAIM-LIMITATION`, not as independent scientific authority.

The supplied answer correctly preserves the frozen R485 arithmetic and refutes
only a stronger physical interpretation that the registered evidence does not
support.  The accepted project-side classification is:

- registered arithmetic: `COMPUTATIONALLY VERIFIED`;
- metric meaning: `construct-limited command-activity metric`;
- literal physical no-harm implication: `refuted_by_counterexample`;
- actual hardware harm/safety: `information_insufficient`;
- frozen R485 status, counts, and source inference: unchanged.

## Intake integrity and independent replay

- The source folder contained eight files.  All seven hashed payload members in
  `DELIVERY_MANIFEST.json` matched their declared byte sizes and SHA256 values.
- The declared input-package digest
  `66a4ae492810e4d64254966a7acfe75a751f93d50138adbcc54f6ce2d5cf68fd`
  matches the project-generated GPT Pro ZIP byte for byte.
- `verification.py` was rerun locally against that original ZIP with CPython
  3.14.3.  It passed 33/33 package hashes, 11/11 sidecars, the 1/1 selected
  problem, 832/832 profile rows, 208/208 policy decisions, all 16 threshold-grid
  cells, and the eight included raw profile files.
- `DERIVED_RESULTS.repo_recheck.json` is identical to the delivered
  `DERIVED_RESULTS.json` after removing the expected runtime-version field.
- The earlier independent project replay remains stronger for data integrity:
  it streamed all 848 evaluation files, 5,088 trajectories, and 763,200 steps.
  The external package independently rechecked only eight representative raw
  profile files and correctly states that boundary.

## Accepted mathematical content

### A. Definition and scaling layer

The formulas for normalized executed-command RMS and total variation match the
registered source.  Within the frozen six-record, 150-step, eight-channel
profile roster, candidate and comparator ratios are dimensionless and
commensurate.  The following consequences are direct algebra and were replayed
locally:

- duplicating complete records leaves RMS unchanged and scales unnormalised TV
  linearly with record count;
- duplicating every channel identically leaves both metrics unchanged because
  both average over channel count;
- common zero-centred scalar rescaling cancels in both ratios;
- RMS and TV respond differently to horizon and action-update-rate changes;
- the ratios are numerically well conditioned for R485 and are far from the
  registered 1.10 ceiling.

The 832-block distributions are reproduced as RMS ratio
`5.748/7.014/9.918` and TV ratio `48.548/85.097/140.251`
(min/median/max).  Therefore `0/208 complete-contract` is not caused by a
near-zero denominator, floating-point noise, or a marginal cutoff.

### B. Construct layer

The registered action terms establish comparator-relative normalized command
amplitude and command path length.  They do not, without an added bridge,
establish actuator energy, wear, fatigue, thermal load, absolute safety, or
deployment no-harm.  This boundary is independently supported by the project
source:

- the normalized-to-M/D decoder is sign-asymmetric (`+600` versus `-200`) and
  lower-clamped;
- M and D channels have different control meanings but enter the registered
  normalized summary with equal weights;
- no selected R485 artifact contains an actuator transfer function, hardware
  rating, damage functional, or comparator safety certificate;
- evaluation uses deterministic policy means and does not establish a
  stochastic deployment distribution.

The two counterexamples are logically valid for the claimed impossibility of a
universal physical implication.  They are not evidence that the actual R485
plant contains the hypothetical downstream deadband or quadratic hardware
damage law.  Their role is to prove insufficiency of the current premises, not
to diagnose actual hardware harm.

### C. Conditional bridge

Under a common calibrated linear action-to-physical map, common bandwidth/time
grid, explicitly named quadratic effort and path-length wear proxies, no omitted
damage terms, and an independently safe comparator, the registered guards imply
an upper relative bound.  With multiplier `m=1.10`, the RMS-derived quadratic
term is bounded by `m^2=1.21`, not by 1.10.  This is a correct conditional
calculation but a simple claim-boundary lemma, not a novel standalone theorem.

## Quarantined interpretations

The following statements are not admitted into project authority:

- that the R485 learned policies caused physical or hardware harm;
- that `0/208` estimates a 100% failure probability;
- that the comparator is an absolutely safe controller;
- that MARL is generally unsafe or incapable on VSG systems;
- that the hypothetical counterexample models describe the actual plant;
- that the conditional 1.21 bound applies to R485 without new calibration.

## Research and publication value

### What is genuinely valuable

R485 supplies a sizeable, traceable negative evaluation rather than a new
algorithm: an all-fresh 208-cell, 26-paired-seed factorial on the corrected
60-Hz path; a strong development-selected deterministic comparator; a frozen
four-profile benchmark; 121/208 endpoint-qualified policies; universal and
large comparator-relative command-activity failures; and no registered source
contrast above the 10% materiality boundary after Holm correction.  The useful
scientific observation is the separation between endpoint improvement and
implementable command regularity in the tested family, together with an audit
showing that actor/critic/reward-source attribution is not established.

This is sufficient research value for a bounded ICEMS-style evaluation or
negative-result paper if the paper is framed as a finite-benchmark,
guard-first evaluation study.  Its contribution is empirical protocol,
traceability, and the sharply measured endpoint/command-activity separation.

### What is not valuable enough on its own

The GPT Pro scaling identities, counterexamples, and `1.10^2=1.21` conditional
bound are mathematically elementary.  They should protect the manuscript's
semantics, not be advertised as a theorem contribution.  The present evidence
does not support a physical-safety paper, a causal endpoint-versus-stress
trade-off, a general MARL conclusion, or a TPWRS-level claim by itself.  A
stronger journal claim would need a prospectively registered physical command
or actuator model, calibrated channel weights and absolute limits, a learned
fresh bank, and preferably a causal repair or constructive learned method.

## Current manuscript impact

The current `main.tex` predates the final R485 authority and is not
submission-ready.  It still reports R483/R484 values (`126/208`, 408 RoCoF
failures, 45 peak failures, and the older source-effect p-values) instead of the
R485 values (`121/208`, 397, 37, and non-rejecting R485 factorial statistics).
It also repeatedly uses `action-stress`, `physical/action no-harm`, and
`command-stress` wording that can be read more strongly than the registered
metric permits.

Required repair before submission:

1. replace all R483/R484 learner counts, factor statistics, figures, and tables
   with R485 authority;
2. rename the action terms to comparator-relative normalized command RMS and
   command total variation, or the shorter `command-activity guard`;
3. state explicitly that these terms are empirical command-regularity
   tolerances, not physical stress or safety certificates;
4. retain `VALID-MIXED`, `121/208`, and `0/208`, while limiting them to the
   frozen finite benchmark;
5. keep the conditional physical bridge and counterexamples to a short
   limitation paragraph or supplement; do not promote them as novelty;
6. regenerate the learned-contract figure and rerun the full manuscript and
   evidence audit before any submission package is treated as current.

## Theory-intake classification

- algebra/definition layer: accepted after repo-side replay;
- mechanism prediction about actual hardware harm: `undecidable` and
  `not-pursued` in R485 because no actuator transfer/damage state or absolute
  safety margin exists in the sealed traces, and R485 forbids new post-hoc
  simulation;
- paper-level mathematics: not promoted as a theorem contribution; retained as
  a verified claim-boundary argument and wording repair;
- frozen experimental verdict: unchanged.

## Final project-side verdict

The answer increases the paper's defensibility but reduces the permissible
strength of its physical framing.  The study remains worth writing as a narrow,
rigorous negative evaluation paper.  It is not presently a physical-safety or
high-tier journal result, and the existing manuscript must be refreshed before
it can represent R485.
