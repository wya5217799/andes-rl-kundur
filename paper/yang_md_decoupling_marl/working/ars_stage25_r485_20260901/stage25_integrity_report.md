# ARS Stage 2.5 Integrity Report — R485 manuscript

Snapshot date: 2026-09-01
Draft snapshot: `paper/yang_md_decoupling_marl/manuscript/main_r485.tex`
Draft snapshot SHA-256: `ccc1d1772a0fee14a421e5598f808229b3a7b5a1f55c49214965420afcc97121`
PDF snapshot SHA-256: `9249501ea91fb6b0d509f6796549eeb1582b75694a57d37eb9394507e6ba09f8`
Headline authority: `CLM-1525/R485`
Post-hoc support only: `CLM-1530/R486`

## Checkpoint verdict

**PASS WITH NOTES.** No open reference fabrication, citation distortion,
numerical mismatch, claim-evidence mismatch, figure/caption mismatch, causal
overreach, safety overreach, or unresolved ARS mechanical claim candidate was
found after correction. The two notes are non-blocking:

1. This is a mid-pipeline intake from a repository-native formal research round,
   so no earlier ARS Material Passport exists. The hash-bound R485 formal seal,
   result manifest, R486 derivative intake, parameter card, and repository feed
   are used as the provenance authority.
2. Originality checking is a protocol-sized Web sample, not an exhaustive
   commercial plagiarism scan.

The ARS workflow requires an explicit owner checkpoint before Stage 3 full
review. Stage 3 has not started.

## Scope and immutable boundaries

- Exact title retained: *Decoupling-Oriented Coordination of Paralleled VSGs
  With Multi-Agent Reinforcement Learning*.
- The accepted digest constrains the title only.
- No experiment, ANDES run, training, evaluation, threshold sweep, or new trace
  was created.
- Six-second and 30-second results remain separate views of shared traces and
  are not treated as independent replications.
- Comparator-relative command RMS and TV remain command-activity summaries,
  not energy, wear, damage, hardware limit, physical safety, or deployment harm.
- R486 diagnostics remain post-hoc recorded-path support and are not causal
  mechanism identification.
- `manuscript/main.tex` remains an untouched donor, not the edit base and not
  scientific evidence.

## Phase A — Reference integrity

Rendered reference population: **16** unique keys. Verified: **16/16 (100%)**.
Ghost, fabricated, metadata-mismatched, or unresolved rendered references:
**0**. The dormant BibTeX entries that are not rendered are outside this
population.

The itemized audit is in `reference_audit.json`. Verification used DOI,
publisher, official proceedings, or institutional records, including IEEE/DOI
records for Zhong, Wu, González-Cajigas, Yang, Cui, and Fu; ScienceDirect for
Liu, Benhmidouch, and Kang; MDPI for Lu and Zhang; the Strathclyde repository
for Shi; the NeurIPS proceedings for Agarwal; PMLR for Haarnoja; and JSTOR for
Holm.

## Phase B — Citation-context integrity

Citation-context population: 16 rendered references. Checked: **16/16 (100%)**,
above the protocol minimum of 30%. Open citation-context distortions: **0**.

Two integrity repairs were applied:

1. The ANDES citation previously carried the project-specific claim that ANDES
   stores runtime M/D parameters on the system base. It now supports only the
   ANDES hybrid symbolic--numeric framework; the base/storage statement is
   explicitly assigned to this project's parameter card.
2. A broad assertion that all cited studies lack a shared benchmark object was
   replaced by the narrower, supportable statement that controller-specific
   models and evaluation contracts are not treated as numerically
   interchangeable with this benchmark object.

No scientific result or conclusion changed.

## Phase C — Data, method, figure, and provenance integrity

The exact R485 and R486 decision artifacts retain their registered hashes:

- R485 formal analysis:
  `2dad35d8e7f559bbcfa124dbae3628aa0d9ceae3ccfbe77996330c891927409b`.
- R486 analysis:
  `75c911f83a9f50c9f208e94c18c039a3b170d09d2575f7396958dcf16b1b257c`.

`data_claim_audit.json` contains **25/25 passing** reproductions and boundary
checks. It covers inventory, endpoint/complete-contract counts, all five guard
failure counts, the 16 sensitivity cells, non-pooled horizons, the four direct
M/D ratios, the seed-501 example, both source-contrast tables and Holm values,
R486 break-even/Pareto/command summaries, training disclosure, bounded previous
action diagnostics, parameter-card values, title, boundary language, and figure
presence.

Figure source and output hashes:

- `build_figures.py`:
  `fa5c9a5a96bf991b7798365bf2bb2b90e597f25673ecba558be39d645efdafc7`.
- Direct-M/D figure:
  `0e510fafd5946d7182ef034abb019b6d60502105469bcfdbd55ec23a8534a935`.
- Learned-contract figure:
  `97bb9eb5b114604023feb59a0355979439b81a5981449445db60fda066ecae3a`.

Both figures, captions, axes, counts, threshold lines, and claim boundaries were
checked against the registered result surfaces. The rebuilt PDF has six A4 IEEE
two-column pages, no undefined citation/reference, no overfull box, and no
visible clipping, overlap, unreadable glyph, or malformed reference. The two
underfull-vbox notices are whitespace only.

Required provenance boundary:

> This check verifies disclosure and claim-to-provenance fidelity. It does not judge whether the experiment was correctly designed, run, statistically adequate, or reproducible by ARS.

## Phase D — Originality and donor boundary

The exact-phrase Web sample covered **12/32 prose paragraphs (37.5%)**, with
coverage across Introduction, contract/method, evaluation design, results,
discussion, and conclusion. Exact overlap hits: **0**. Returned fuzzy results
were unrelated or shared only generic words. The query list is fixed in
`originality_audit.json`.

Local donor screening found a 12-word-shingle overlap fraction of **9.88%**.
The longest shared runs are author/title material, equations, registered
parameter strings, and TikZ layout syntax. This is consistent with the allowed
donor roles of structure, expression, layout, method explanation, and literature
leads. The donor is an unpublished same-project draft and is not used as
scientific authority.

## Phase E — Claim verification

Semantic high-impact claim groups: **26**. Every group was selected; no random
top-up was needed. Exact source-bound Evidence Rows: **41**, spanning all 26
groups and all 16 rendered external references. ARS Evidence Row validation and
explicit source-map replay: **PASS, 41/41**.

The Claim Registry contains 26 semantic groups plus 13 mechanical LaTeX
sentinels. Mechanical coverage reports **0 unregistered candidates**; replay
validation is **PASS**. Semantic extraction completeness remains correctly
reported as `not_machine_detectable`, so the human semantic population and the
mechanical detector result are kept distinct.

Claim verdicts: **41 VERIFIED, 0 MINOR_DISTORTION, 0 MAJOR_DISTORTION,
0 UNVERIFIABLE, 0 UNVERIFIABLE_ACCESS** after the Phase B repairs.

## Seven AI research failure modes

| Mode | Verdict | Decisive evidence |
|---|---|---|
| 1. Implementation bug mistaken for science | CLEAR within the sealed scope | R485 formal seal and hashes; 1,082/1,082 terminal artifacts; 5,088/5,088 trajectories; no missing/hash/parse invalid item; R486 independent recomputation reproduced the registered surfaces. This does not claim absence of every latent bug. |
| 2. Citation hallucination | CLEAR | 16/16 rendered references verified against DOI, publisher, official proceedings, or institutional records. |
| 3. Hallucinated result or unsupported number | CLEAR | 25/25 numerical and boundary checks pass against hash-valid R485/R486 and the parameter card; figures match those surfaces. |
| 4. Shortcut exploitation mistaken for generalization | CLEAR for this manuscript's claim | The paper makes no policy-success, topology-generalization, deployment, or fresh-bank learner claim; qualification failure is reported directly on the fixed benchmark. |
| 5. Bug-as-insight or surprise inflation | CLEAR | No surprising/counterintuitive mechanism claim is made. R486 sensitivities are explicitly post-hoc, bounded, and non-causal. |
| 6. Methodology fabrication | CLEAR | Base conversion, action map, network, reward, seeds, budget, horizons, guards, tests, multiplicity, and banks trace to the parameter card, frozen plan/source, and formal artifacts. |
| 7. Frame lock-in despite contradictory evidence | CLEAR | The accepted title is retained without importing digest claims; the manuscript is organized around the R485 qualification reversal and keeps R486 subordinate. |

## Outputs

- `claim_registry.json` — exact-byte semantic and mechanical claim population.
- `claim_registry_coverage.json` — mechanical coverage result and replay target.
- `evidence_rows.json` — 41 ARS Evidence Rows.
- `data_claim_audit.json` — 25 reproducible data/method/boundary checks.
- `reference_audit.json` — 16/16 reference and citation-context audit.
- `originality_audit.json` — 37.5% paragraph sample and donor screen summary.
- `donor_overlap_audit.json` — local shingle and contiguous-match details.

## Disposition

This Stage 2.5 manuscript snapshot was integrity-cleared for the next ARS stage,
with the two non-blocking notes above. Per the mandatory ARS checkpoint, no Stage 3 full
review, adversarial review, journal-fit review, or further substantive rewrite
should begin until the owner confirms continuation.
