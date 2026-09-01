# Start writing — `yang-md-decoupling-marl`

Use this file to find the current paper material. It is an index, not evidence.
Scientific facts remain in current claims, feeds, and hash-valid result JSON.

For a compact paper-facing fact sheet, read `PAPER_EVIDENCE.md` next. It
compresses the R485 headline, R486 precision/mechanism addenda, safe wording,
figure/table choices, and exact source hashes. Return here only for manuscript
history, the Introduction hard-flaw gate, and the full writing sequence.

## Three manuscript generations

| Generation | Main artifact | What remains useful | What is no longer current |
|---|---|---|---|
| First paper | `manuscript/manuscript.md` | Early structure, explanations, and literature leads | The draft and its numerical story are superseded. |
| Second paper | `manuscript/main.tex` and `main.pdf` | Current IEEE six-page structure, author block, equations, verified references, and much of Methods | It is a pre-R485 revision. R483/R484 learned-policy counts, figures, captions, and source-effect text are stale. |
| Current paper | author `manuscript/main_r485.tex` | Reuse only source-checked donor material from the second paper | No new draft has yet absorbed R485. |

## Reauthoring intent — binding handoff

Write the R485 paper as a fresh manuscript body in
`manuscript/main_r485.tex`. Treat `manuscript/main.tex` as a frozen pre-R485
donor, not as the editing base. Keep it available for comparison until the new
draft passes source review and PDF review; promotion to the canonical
`main.tex` is a finalization step.

This is a scientific rewrite, not a numerical refresh. R485 changed the
load-bearing account of the work:

- learner and comparator paths now use the canonical 60-Hz transformation
  exactly once;
- the evidence is all-fresh and uses a fixed 43,200-step budget with the final
  checkpoint as the paper result;
- the registered guard is comparator-relative normalized command activity,
  not actuator stress, wear, hardware safety, or a generic no-harm claim;
- endpoint success, complete-contract qualification, source inference, and the
  30-second deterministic gate must remain separate results.

Start from the R485 claims and result JSON, then import old prose only when it
still expresses those authorities. Do not browse all of `working/`; use only
the branches below.

### Donor material

The new draft may reuse the IEEE preamble, author block, bibliography leads,
system equations, device-base M/D parameterization, coordinate definitions,
profile definitions, and deterministic-comparator setup. Check each imported
block against the current claims before keeping it.

Rewrite the abstract, problem framing, contributions, learner protocol,
training/checkpoint account, contract semantics, results, figures, tables,
captions, discussion, limitations, and conclusion. The old body's section
order is optional; use it only where it helps the R485 argument.

### Fixed title and accepted digest

The owner confirmed that the ICEMS one-page digest was accepted and made the
scope decision that **only its title is binding on this full-paper rewrite**.
Keep the exact title in `LINE.md`; retitling is outside this writing pass. The
digest is a preliminary submission artifact, not scientific evidence or a
template for the current question, method, contribution, result, or conclusion.

Neutralize its success-style reading in the paper itself. The opening two
sentences of the abstract and the first Introduction paragraph must identify
the work as a bounded, guard-first evaluation and state the endpoint-only
result. Use *coordination* for the investigated MARL formulation, not for an
achieved complete-contract qualification.

Do not force the new paper to preserve the digest's HAWE contribution, intended
objective, LS1/LS2 table, figure, or success-style conclusion. Import any such
item only if it is independently supported by current R485/R486 authority;
otherwise omit it. Before finalization, check only normalized title identity
and ordinary submission metadata against the accepted record. Scientific
consistency with the digest is not a manuscript gate.

### Introduction hard-flaw gate — `intro-drafter`

Use `intro-drafter` for the first prose pass and position this as a **New
Problem/Setting evaluation paper**, not a successful Technique paper. Its
load-bearing problem is whether endpoint improvement qualifies a corrected
M/D-MARL policy under a complete endpoint-plus-command-activity contract. The
MARL controller is the evaluated object, not the claimed new solution.

Close the skill's six-paragraph chain before drafting the rest of the paper:

1. Ground the motivation in one real R485 running example. A suitable
   candidate is `an_cn_r0`, seed 501: its aggregate endpoint ratios are
   0.535918 and 0.905632, yet all four profile guards fail. Label it as an
   illustration and return from it to the 121/208 versus 0/208 population
   result. Source:
   `formal_analysis.json#/threshold_sensitivity/primary/policy_decisions` and
   `/per_profile_blocks`.
2. State at most three limitations of prior VSG/MARL evaluation, each supported
   by a verified source. Recheck the nearest-work citations; do not turn model
   memory or the old Introduction into novelty evidence.
3. Make the research question and hard constraints explicit: corrected
   exactly-once 60-Hz semantics, all-fresh policies, profile-complete guards,
   separated 6-second/30-second horizons, and finite-benchmark inference.
4. Use three challenges only: semantic comparability, endpoint-versus-contract
   qualification, and source attribution under paired-seed variability.
5. Map them one-to-one to the corrected parameter/comparator contract, the
   guard-first non-pooled evaluation, and the matched source factorial.
6. Claim three contributions only: the qualification problem/contract, its
   prospective evaluation design, and the bounded R485 empirical finding.
   Each contribution must name its delivering section and R485 evidence.

The gate passes only when every arrow above closes, every cited limitation is
verified, every contribution maps to a section and evidence object, and a
30-second read of the title plus abstract plus Introduction opening cannot be
mistaken for a successful-MARL claim. Until then, repair the Introduction plan
instead of filling the rest of `main_r485.tex`.

## Current story

The paper remains a bounded ICEMS 2026 evaluation paper with the fixed title in
`LINE.md`. R485 closes the experiment side:

- 121/208 all-fresh policies meet both aggregate 5% decoupling endpoints, but
  0/208 pass the complete registered contract.
- All 832 policy-profile blocks exceed both comparator-relative normalized
  command-RMS and command-total-variation limits; 397 also fail RoCoF and 37
  fail worst-frequency peak.
- No registered 6-second or separate 30-second source contrast establishes its
  positive material effect after Holm control.
- The direct-M/D comparator passes the separate 30-second fresh-bank gate on
  4/4 profiles.

Bind this wording to `CLM-1525`, `reports/R485.md`, and the R485 result JSON.
Command RMS/variation are command-activity summaries, not actuator stress,
wear, hardware safety, or deployment evidence. Non-rejection is not zero effect
or equivalence. The finite benchmark is not a universal MARL verdict.

## Current evidence to use

| Purpose | Claim/feed | Raw data |
|---|---|---|
| Corrected M/D semantics | `CLM-1485`, `CLM-1490`; `reports/R478.md` | `working/md_parameter_card_20260824.json`; `results/research_loop/r478_port_unseen/formal_analysis.json` |
| Why every paper result needs a 30-second tail | `CLM-1495`, `CLM-1500`; `reports/R480.md` | `results/research_loop/r480_h_sensitivity/analysis.json` |
| Deterministic comparator selection and 6-second fresh gate | `CLM-1505`; `reports/R481.md` | `results/research_loop/r481_direct_md/formal_analysis.json` |
| Interrupted run kept out of inference | `CLM-1510`; `reports/R482.md` | `results/research_loop/r482_u2_confirmatory/closeout_audit.json` |
| Final learned-policy, guard, source-factorial, and 30-second deterministic result | `CLM-1525`; `reports/R485.md` | `results/research_loop/r485_60hz_source_factorial/r485-formal-20260829-a/formal_analysis.json` |
| Post-hoc precision, Pareto, M/D channel distributions, and bounded mechanism diagnostics | `CLM-1530`; `reports/R486.md` | `results/research_loop/r486_r485_posthoc_intake/analysis.json` |
| Quasi-static RMS recurrence check | post-hoc working addendum; `working/r485_quasistatic_rms_grid_20260831/REPORT.md` | `working/r485_quasistatic_rms_grid_20260831/result.json` |
| Finite-record TV/RMS mathematical audit | project-side `ADVERSARIAL QUALIFIED PASS`; `working/gpt_pro_r485_mechanism_math_20260901/COMPARATIVE_ADVERSARIAL_REVIEW.md` | both return folders, with the passing second verifier and independent checks in `GPT_PRO_RETURN_V2/REPO_RECHECK.json` |

R483/R484 are design and supersession history only. Their legacy 50-Hz learner
numbers must not enter the current abstract, results, figures, or conclusion.

Inside the R485 `formal_analysis.json`, start from:

- `/inventory` and `/status` for validity and terminal classification;
- `/learner_qualification` for endpoint versus complete-contract counts;
- `/threshold_sensitivity/primary/per_profile_blocks` and
  `/threshold_sensitivity/grid` for guard counts and the offline sensitivity;
- `/primary_inference/tests`, `/tail_inference/tests`, and `/source_inference`
  for the two non-pooled source analyses;
- `/fresh_bank_deterministic_gate` and `/same_bank_deterministic_gate` for the
  separated deterministic results.

Use R486 to make R485 easier to interpret, not to replace its headline. The
break-even distance, Pareto count, and M/D command-activity distributions can
support Results; the exact-inversion bounds must be labelled post-hoc. Keep the
previous-action, quasi-static-setpoint, projection, and failed-intervention
diagnostics in Discussion or a supplement and use consistency language rather
than causal language. Report the 208/208 entropy-temperature-floor observation
as a training-dynamics limitation, never as proof of convergence failure.

The expanded quasi-static RMS check prevents a stronger mechanism claim. On
the frozen 24-policy x four-profile grid, the constant-anchor/actual raw-RMS
ratio has median 0.959, but only 141/192 channel ratios meet 0.90 (D 87/96; M
54/96). For the one included checkpoint, temporal variation still contributes
37.45%--51.23% of raw RMS-squared energy. In Discussion, report comparable
aggregate norm as a finite-grid observation, especially for D; do not call the
output quasi-static or the anchor a dominant source. The full-record anchors
use future values and are post-hoc diagnostics, not an online information
pattern, endpoint intervention, or stability test.

The two external finite-record audits agree on one narrow structural fact:
with the registered common zero reset, the exact normalized componentwise
limiter is total-variation diminishing, with a terminal-residual
strengthening. Do not write “previous-action feedback amplifies TV”; state the
frozen-observation, full-record-mean actor-input replacement and its 48/48
finite-grid result. Do not call the constant-anchor output a dominant or
temporally static RMS source. The second verifier passes repo-side and its
kink-aware path partition survived an independent 257-path audit, but it still
covers only one included checkpoint and no plant counterfactual. Cite the
project-side `ADVERSARIAL QUALIFIED PASS`, not either external completion label.

## Literature and previous analysis

- `manuscript/references.bib` is the bibliography to retain and refresh before
  submission. `paper/icems2026` supplies layout and literature leads only.
- `working/deep_research_c_class_necessity.md` is the main literature/context
  note for the source-factorial question.
- `working/theory_audit_bundle/` is the conditional mathematics reference.
- `working/r402_causal_validation_final_bundle/` explains historical interface
  defects; it is an audit/design aid, not replacement evidence.
- `working/icems_negative_result_acceptance_assessment_20260825.md` supports
  venue positioning only.
- `working/gpt_pro_r485_action_guard_solution_20260831/PROJECT_INTAKE_REVIEW.md`
  owns the command-activity wording boundary; the external answer adds no new
  scientific result.
- `working/r485_bounded_negative_results_research_20260831.md` preserves
  literature leads recovered from the paper-route conversations. It is not
  evidence; re-open and verify every cited primary source before use.

For exhaustive history, `LINE.md` maps every claim to its feed and
`ARTIFACTS.json` lists every registered document. Open them only when a current
claim or paragraph needs that history.

## Writing sequence and completion

1. Create `manuscript/main_r485.tex` with only the reusable formatting and
   identity material, then write the R485 argument from the evidence above.
2. Regenerate learned/factorial figures and tables from the R485 JSON. Keep the
   R481 direct-M/D figure only with its correct 6-second role.
3. Keep 6-second primary and 30-second tail analyses separate. Label the
   benchmark profiles as outcome-visible frozen records and preserve the
   finite-benchmark claim ceiling.
4. Source-check every paper-facing number and remove all live remnants of the
   legacy 50-Hz path, adaptive stopping account, 126/408/45 counts, and
   actuator-stress/no-harm wording.
5. Rebuild the candidate PDF and refresh the artifact inputs,
   claim-evidence/domain audit, bibliography check, and submission package.
6. Promote the reviewed candidate to canonical `manuscript/main.tex`; preserve
   or archive the pre-R485 donor with an explicit superseded label.

No new experiment is part of this writing pass.
