# Field Analysis Report

## Scope and binding status

- Source reviewed: `paper/yang_md_decoupling_marl/manuscript/main.tex`
- Source SHA-256: `A19922C9B3E330FEC5ABE682A9737A108B5ABA2782563898C7453589B2EE9277`
- Metadata reviewed: `paper/yang_md_decoupling_marl/working/ars_review_20260828/metadata.json`
- Review mode: ARS academic-paper-reviewer, Phase 0 only
- Criteria binding: `criteria_binding_unavailable`
- Calibration status: `NOT_CALIBRATED`
- Target context: ICEMS 2026 is author-provided background only. No ReviewTargetContext, ReviewCriteriaBindingManifest, or venue-criteria brief was supplied; this report makes no formal venue-criteria alignment or venue-fit claim.

## Paper Basic Information

- **Title**: Decoupling-Oriented Coordination of Paralleled  VSGs With Multi-Agent Reinforcement Learning
- **Language**: English
- **Abstract length**: approximately 227 words after LaTeX-markup stripping
- **Full text length**: 4,699 words (metadata value)
- **References visible from the reviewed source**: 24 unique citation keys in `main.tex`; the bibliography database was outside this Phase 0 read scope

## Field Analysis

| Dimension | Analysis Result |
|---|---|
| Primary Discipline | Electric power engineering, specifically power-system dynamics and control of paralleled virtual synchronous generators (VSGs) in a modified Kundur system. |
| Secondary Disciplines | Grid-forming converter control; multi-agent reinforcement learning; computational experimental design and statistical inference. |
| Research Paradigm | Quantitative, simulation-based comparative research with a prospective factorial audit. |
| Methodology Type | Controlled time-domain simulation; deterministic-controller comparison; a matched-seed $2\times2\times2$ actor-source, critic-source, and reward-access factorial; multiplicity-controlled paired inference; guard-first policy qualification. |
| Target Journal Tier | `criteria_binding_unavailable`. ICEMS 2026 is context only. No Q-tier or venue fit is inferred. Field-generally, the manuscript has the scope and compression of a mature IEEE-style conference paper. |
| Paper Maturity | Pre-submission-level draft as a field-general observation: the manuscript has a complete IEEE conference structure, explicit estimands, figures/tables, limitations, and bounded conclusions. This is not a submission-readiness or venue-compliance determination. |

## Central contribution and review-sensitive boundaries

The manuscript presents an evaluation design rather than a new MARL algorithm. It separates endpoint improvement from a complete guard-first contract after correcting device-to-system-base conversion. Its central bounded result is that 126 of 208 frozen policies meet both aggregate endpoint targets on the canary bank, while none passes the complete contract because all 832 learned policy--profile blocks violate both registered relative action-stress limits. The deterministic fresh-bank result, learned-policy canary result, 6 s primary horizon, and 30 s sensitivity are explicitly non-pooled.

Phase 1 should therefore keep four questions distinct: physical correctness of the VSG and base-conversion model; inferential validity of the matched-seed factorial and Holm-controlled claims; evidentiary meaning and sensitivity of the empirical guard thresholds; and the boundedness of claims across banks, horizons, topology, communication assumptions, and hardware validation. Phase 0 did not verify numerical results against external evidence artifacts.

## Venue Recommendation Status

No target-journal list is produced. `criteria_binding_unavailable`. Naming substitute venues or reconstructing ICEMS 2026 criteria from memory would create an unsupported venue-alignment claim.

## Reviewer Configuration Cards

### Reviewer Configuration Card #1

**Role**: EIC
**Display role**: Journal-Fit Reviewer
**Identity Description**: A senior power-systems-control publication reviewer experienced in evaluating compact conference manuscripts on converter-dominated grids, with emphasis on whether an evaluation-design contribution is clearly distinguished from a controller-design contribution. This is a field-general persona, not an ICEMS 2026 criteria expert.
**Criteria binding**: `criteria_binding_unavailable`
**Calibration status**: `NOT_CALIBRATED`
**Review Focus**:

1. Clarity and significance of the endpoint-versus-complete-contract contribution.
2. Consistency of the paper's bounded claims across abstract, results, discussion, and conclusion.
3. Accessibility of the contribution to power-systems and converter-control readers without making a formal venue-fit judgement.

**Will particularly care about**: Whether the paper consistently presents a finite-bank evaluation result rather than a universal failure claim about MARL.
**Possible blind spots**: Detailed statistical reconstruction and low-level simulator/model semantics.

### Reviewer Configuration Card #2

**Role**: Peer Reviewer 1
**Display role**: Peer Reviewer 1 — Methodology
**Identity Description**: A computational power-systems methodologist specializing in multi-seed reinforcement-learning evaluation, matched factorial designs, nonparametric paired inference, multiplicity control, and reproducible simulation studies.
**Criteria binding**: `criteria_binding_unavailable`
**Calibration status**: `NOT_CALIBRATED`
**Review Focus**:

1. Correctness of the inferential unit, within-seed contrasts, materiality boundary, exact Wilcoxon route, and Holm family.
2. Separation of development, training, fresh, and canary banks and of the 6 s and 30 s horizons.
3. Reproducibility and auditability of the 208-policy factorial, stopping rule, frozen checkpoints, and reported denominators.

**Will particularly care about**: Pseudoreplication, post-selection leakage, and whether failure to establish a material effect is kept distinct from equivalence or zero effect.
**Possible blind spots**: Grid-forming control realism and deployment constraints beyond the registered simulation design.

### Reviewer Configuration Card #3

**Role**: Peer Reviewer 2
**Display role**: Peer Reviewer 2 — Domain
**Identity Description**: A senior power-system dynamics and grid-forming-converter researcher specializing in VSG swing-equation modelling, per-unit base transformations, virtual inertia and damping coordination, and time-domain validation in multi-machine benchmark systems.
**Criteria binding**: `criteria_binding_unavailable`
**Calibration status**: `NOT_CALIBRATED`
**Review Focus**:

1. Physical consistency of the device/system-base conversion, $M=2H$ convention, frequency scaling, decoder, projection, and runtime application path.
2. Interpretation of common and differential coordinates and finite-window response energies.
3. Whether empirical guards support only tested-bank no-harm decisions and avoid stability, safety, or hardware-certification claims.

**Will particularly care about**: Whether the corrected physical object and comparator are defined tightly enough for the numerical conclusions to be meaningful.
**Possible blind spots**: Detailed statistical operating characteristics and broader safe-RL governance.

### Reviewer Configuration Card #4

**Role**: Peer Reviewer 3
**Display role**: Peer Reviewer 3 — Cross-disciplinary/Practical
**Identity Description**: A safe reinforcement-learning and cyber-physical-systems researcher specializing in constraint-aware policy evaluation, actuator-stress metrics, distribution shift, communication imperfections, and the gap between simulation qualification and deployability.
**Criteria binding**: `criteria_binding_unavailable`
**Calibration status**: `NOT_CALIBRATED`
**Review Focus**:

1. Whether reward optimization, endpoint improvement, and verified constraint satisfaction remain conceptually separate.
2. Sensitivity and practical meaning of comparator-relative action-RMS, action-variation, saturation, and no-harm thresholds.
3. External-validity limits arising from one topology, ideal synchronous communication, finite profiles, and absence of EMT/HIL evidence.

**Will particularly care about**: Whether the complete contract is framed as an empirical decision rule rather than a safety certificate, and what evidence would be needed for deployment-relevant claims.
**Possible blind spots**: Fine-grained VSG parameter semantics and the exact power-system literature lineage.

## Review Strategy Recommendations

- Keep the four card-backed perspectives distinct: publication framing, statistical design, physical-domain validity, and safe-RL/deployment interpretation.
- The fixed Devil's Advocate should test the strongest alternative explanation: whether the headline separation depends materially on the registered comparator and guard thresholds, while respecting that the manuscript already limits its claims to the tested contract.
- All later seat outputs must retain `criteria_binding_unavailable` and `NOT_CALIBRATED`; none may claim formal ICEMS 2026 criteria alignment.
