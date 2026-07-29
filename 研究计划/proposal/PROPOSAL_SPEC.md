# Research Proposal — agreed spec (grill-with-docs session, 2026-06-09)

**Status:** APPROVED scope → drafting.

## Purpose & audience
- Application material for **UNNC Master by Research (MRes), Electrical & Electronic Engineering**.
- Primary reader = **university admissions committee** (not a VSG specialist). Must read clean, be accessible to a non-expert, look professional, and *feel impressive*.
- Supervisor (Dr John Xu) already informally agreed; proposal's job is to pass the school gate + justify "why this MRes / why continue this line".

## Hard constraints (from 研究计划要求.md)
- English. 1000–3000 words (target ~2200–2400 body words).
- Required sections: Introduction (theoretical + empirical background), Literature Review, Methodology, Contribution, Bibliography.
- Professional typesetting → **LaTeX → PDF**.

## Direction (v2 — sharpened, user-driven)
- Umbrella: **distributed / multi-agent intelligent (RL) control of VSGs** for low-inertia grids.
- **Headline forward thrust = industrial deployability via topology generalization.** Core motivation: per-topology RL needs 91 trials / 250+ rounds on ONE network → infeasible for utilities running many topologies.
- Research questions: RQ1 **necessity** (when does RL beat well-tuned classical droop enough to justify cost — framed as cost-benefit, NOT defeatist); RQ2 **limitations** of per-topology agents; RQ3 **(core)** **GNN-based topology-general agent** (grid = graph) that transfers across topologies without retraining.
- **NOT** the fidelity/EMT/sim-to-real pivot (rejected as "too far"); also dropped the earlier reward-shaping framing in favour of the GNN/deployability framing.
- New refs added: `owerko2020opfgnn`, `liao2022gnnreview` — **VERIFIED 2026-06-09** (authors/title/venue/volume/pages/DOI confirmed via web; ICASSP 2020 and JMPCE 10(2):345-360, 2022).

## Presentation feedback (v2)
- Must read as **concrete proof of work done**, not smooth exposition. → added a "by-the-numbers" block + a 12-row algorithm table (variant / function / outcome), more declarative findings.

## Emphasis
- Centerpiece = **showcase of existing work** (volume of experiments, breadth of methods, what worked, headline results). Light on detail; impressive-feeling.
- **Single-VSG / Stage 1 work: OMITTED** (deemed unimportant).
- FYP (multi-agent reproduction) = starting point; treat the dissertation's old numbers (6-axis, R21 lucky basin) as superseded.
- Ground all "current results" in the **repo (R67–R259)**, not the FYP dissertation.

## Showcase facts (defensible, from README.md / STATE.md)
- Reproduced Yang et al. 2023 multi-agent DDIC (4-VSG SAC) on modified Kundur 4-bus via ANDES.
- Post-FYP programme: **259 rounds (R01–R259)**, **263 audited claims** w/ trust levels, **35+ regression tests**, full traceable audit trail.
- **12 RL algorithm variants** (SAC, SAC-CTDE, TD3, TD3-LSTM + variants, QR-critic, AFE, Transformer).
- **11-axis paper-grade evaluator** (exposes single-axis failure modes).
- **HAWE inference-time ensemble** = project SOTA (4-way cross-algorithm); **RL ≈ 1.99× classical adaptive droop**.
- **Structural plateau** confirmed across **91 trials** + mechanism analysis ("fire-once-hold-saturated", decoupled from disturbance).
- **16-page IEEE-format manuscript** drafted.

## Anchor reference
- Yang et al., *A Distributed Dynamic Inertia-Droop Control Strategy ... for Multiple Paralleled VSGs*, IEEE TPWRS 2023 (`yang2023ddic`). Clean transcription at `Desktop/论文/`.
- Bibliography reuses verified entries from the dissertation `refs.bib` (single-VSG entry `benhmidouch2024td3` NOT cited).

## Files
- `研究计划/proposal/main.tex` — proposal (article class).
- `研究计划/proposal/refs.bib` — bibliography (verified entries).
- `研究计划/proposal/PROPOSAL_SPEC.md` — this file.
