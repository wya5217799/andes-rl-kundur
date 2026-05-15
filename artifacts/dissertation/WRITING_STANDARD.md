# FYP Dissertation Writing Standard

> Consumer: Claude writing this dissertation.
> Source: UNNC rubric + Writing Lab guides in `docs/`.

---

## 0. Hard Rules

1. **Introduction is not marked** — write it for completeness only.
2. **No standalone Literature Review chapter** — cite literature throughout to justify every design decision.
3. **Appendix must contain 4 representative weekly meeting records**, referred to by name in the Management Reflection.

---

## 1. Mark Weights (for effort prioritisation)

| Section | Weight |
|---|---|
| Specification Validation | 15% |
| System Modelling | 10% |
| System Development | 10% |
| Use of Literature | 10% |
| Reflection on Management | 10% |
| Presentation of Results | 10% |
| Wider Context | 5% |
| Communication Quality | 5% |

---

## 2. What Each Section Must Contain

### Design and Implementation — System Modelling
**Must have:**
- Simulation/analytical methods used to model the project.
- Attempt to discuss limitations of the approach.

**To score high:**
- Justify why each method/tool was chosen over alternatives, with respect to the project spec and constraints.
- Discuss trade-offs and limitations explicitly.
- Show the methods successfully address the specification.

---

### Design and Implementation — System Development
**Must have:**
- Show the designed system was taken into implementation (build or refined simulation).
- Discuss challenges encountered and how they were handled.

**To score high:**
- Bespoke methods created by the student — not just out-of-the-box library usage.
- Competency with a range of tools demonstrated.
- Clear progression of methodology following engineering principles; all changes from original plan explained and justified.
- Evidence of sub-system testing before full integration.

---

### Design and Implementation — Use of Literature
**Must have:**
- Literature cited throughout to support the work (not isolated to one section).
- IEEE citation style followed.

**To score high:**
- For every cited source, explicitly state how it was adopted or adapted — do not just cite and move on.
- Use peer-reviewed papers, textbooks, datasheets — not just websites or tutorials.
- Note limitations of the sources where relevant.
- Every major design or development decision has a backing reference.

---

### Testing — Specification Validation *(highest weight: 15%)*
**Must have:**
- Results captured and validated against the project specification list.

**To score high:**
- Explicit pass/fail criteria for every specification point.
- Results compared against expectations from modelling, literature, or component specs.
- Unexpected results explained and the explanation validated.
- Quantitative/statistical analysis to confirm accuracy and repeatability.
- Every specification point addressed; for any unmet point, explain why and assess the impact on the system.

---

### Testing — Presentation of Results
**Must have:**
- Figures and tables with labels, readable axes, correct units.

**To score high:**
- Range of figure/table types appropriate to the data.
- Key features highlighted for discussion (annotations, subfigures, arrows).
- Results ordered logically alongside the discussion.
- Test conditions and procedures stated with justification.

---

### Conclusion — Wider Context
**Must have:**
- Review the final system with respect to health & safety, societal, environmental, commercial, or standards considerations (as applicable).

**To score high:**
- Next-development steps with resource requirements (cost, time), both near-term and long-term.
- Full status summary of every specification point.
- Strong understanding of how the project fits within its societal and industry context.

---

### Conclusion — Reflection on Management
**Must have:**
- Reflect on project management progress.
- Reference the 4 weekly meeting records in the appendix by name.
- Lessons learned discussed.

**To score high:**
- Describe project management skills developed and how they transfer to future projects.
- Support reflections with specific references to the review documents.
- Evaluate whether risk mitigation strategies worked; extract reusable lessons.

---

### Communication Quality
**Must have:**
- Complete document: section headings, page numbers, contents page.
- Readable by a technical person unfamiliar with the project.

**To score high:**
- Consistent styles throughout: headings, layout, captioning.
- List of figures, list of abbreviations, list of symbols included.
- Correct cross-referencing throughout.
- Concise writing with correct grammar and spelling.

---

## 3. High-Risk Missing Items

Missing any of these will seriously limit marks:

- [ ] Specification validation table with explicit pass/fail for every point
- [ ] Results explicitly linked back to specification points
- [ ] Discussion of method limitations and trade-offs
- [ ] Literature used to justify decisions throughout (not isolated)
- [ ] Evidence of original work — not just tutorial code or library defaults
- [ ] Sub-system testing evidence before full integration
- [ ] Test conditions, procedures, units, and labelled figures
- [ ] Appendix with 4 weekly meeting records, referenced in the text
- [ ] Document complete enough for another technical reader to continue or repeat the work

---

## 4. How to Write Each Section

### Writing Order
1. Tables and figures first — forces evidence-first thinking
2. Results
3. Methods / Design
4. Discussion
5. Conclusion
6. Introduction and Abstract last

---

### Section Openers
Every major section opens with:
1. Purpose of this section
2. What it covers
3. How it connects to the overall project argument

**Weak:** jumps straight into procedures.
**Strong:** "This section outlines the steps taken and models chosen to implement the adaptive inertia controller. First, ..."

---

### Methods / Design — How?

Write to be detailed, step-by-step, and replicable.

For this project include: test-system description, VSG mathematical model, RL MDP formulation (state/action/reward), algorithm choice and justification, simulation setup, hyperparameters, training procedure, evaluation metrics.

**A system overview diagram is strongly recommended.**

**Tense:**
- Past tense for completed actions: "The reward function was defined as..."
- Present tense for figures/equations: "Fig. 2-1 shows...", "where $J$ represents..."
- Present tense for definitions: "A VSG is..."

**Voice:**
- Passive to describe the process: "Training was conducted over 500 episodes..."
- Active to highlight decisions: "TD3 was chosen because..."

**Justify every non-obvious choice.** Traditional method → cite papers using the same approach. Novel method → explain limitations of prior work and how this improves on it.

---

### Results — What?

Raw data ≠ Results. Data must be summarised, explained, shown clearly, and interpreted in relation to the project aims.

**Be quantitative:**
- Weak: "The controller performed well."
- Strong: "The settling time was reduced from 1.8 s to 0.9 s, a 50% improvement."

**Tense:**
- Past for what happened: "The reward converged after 300 episodes..."
- Present for figure references: "Fig. 4-1 shows..."
- Present for what results indicate: "The results indicate that..."

**Figures and tables:**
- Figures for trends, comparisons, visual patterns
- Tables for precise multi-parameter values
- Never present the same data in both
- Figure captions **below**; table captions **above**
- Every figure/table referenced in the text before it appears

---

### Discussion — Why?

Use the **discussion sandwich** for each key result:

1. **State the result** — include a number
2. **Compare** — against objective, baseline, simulation, or literature
3. **Explain** — the engineering reason why this happened
4. **Implication** — what this means for the system or design
5. **Restate** — make the meaning explicit

**Template:**
> Fig. X shows that [metric] changed from [value] to [value], a [X%] change. This [agrees with / contradicts] [objective or literature], most likely because [engineering reason]. Therefore, this suggests that [implication]. However, this interpretation is limited by [limitation], so future work should [specific next step].

**Checklist:**
- [ ] Start with a restatement of key results
- [ ] Compare to literature / baseline
- [ ] Explain the engineering reasons
- [ ] Do not introduce new raw data

---

### Conclusion — Did you meet your objectives?

Structure:
1. Restate the project aim
2. Summarise the main method
3. State the most important results with numbers
4. Explain whether and how objectives were met
5. State the contribution
6. List specific limitations
7. Propose concrete future work

**Template:**
> This project aimed to [main objective]. To achieve this, [method/system] was designed, implemented, and evaluated using [test method]. The results showed that [key result 1] and [key result 2]. These findings indicate that the project [met / partially met] its objectives because [reason]. The main contribution is [specific contribution]. However, the study is limited by [specific limitation]. Future work should focus on [specific realistic improvement].

---

## 5.5 Hub Doc Entry (新对话进来必读)

**3 hub doc 体系** + 16 evidence pack 共构 dissertation 写作输入层.

| Doc | 视角 | 何时用 |
|---|---|---|
| `CONTEXT.md` (本目录) | 论文 SPEC + 错误防护 + 5 bespoke + 数字版本 §11 | 写 main.tex / 校对 / 防 over-claim |
| `Multi-Agent VSGs/CONTEXT.md` | ANDES 工程视角 (round / branch / env / failure / plan 生态) | 改代码 / 找 verdict / 答辩 |
| `Multi-Agent VSGs/RESEARCH_TRAIL.md` ⭐ | **因果链** R01-R37 + commit + 6 拐点 + type-view filter | **写 §4.5 Reflection / §3.3 Findings 主源** |

**Evidence Pack 16 个** (`plan/evidence/`):
- A 系列 (2): A1 Stage 1 / A2 Stage 2 ANDES (post-fix headline) ⭐
- B 系列 (4): B1-B4 Engineering decisions
- C 系列 (5): C1-C4 + **C5 HAWE (Asset 5, v16 升级)** ⭐
- D 系列 (4): D1-D4 Failures (含 F1-F6 失败树)
- E 系列 (2): E1 PI-TD3 pivot / E2 4-role AI

**入口顺序** (新对话):
1. WRITING_STANDARD.md (本文件, 写作规范)
2. CONTEXT.md (事实 + post-fix 数字)
3. Multi-Agent VSGs/RESEARCH_TRAIL.md (因果)
4. plan/evidence/EP-{A1-E2}.md (按章节抓输入)
5. Multi-Agent VSGs/CONTEXT.md (按需深入)

---

## 5.6 Post-Ranker-Fix 数字 (论文必用, 2026-05-08 L3 锁定)

⚠ ANDES 6-axis score 在 2026-05-07 ranker fix 后推翻. 论文 main.tex headline **必用 post-fix**.

| 数 | Pre-fix (旧 verdict / sprint memo) | **Post-fix (论文用)** |
|---|---|---|
| R21 V4_h50_s49 single | 0.613 / 5.57× no_ctrl | **0.444 / 4.04× no_ctrl** |
| HAWE w9802 (98% R21 + 2% ws8) | 0.607 / 5.52× / 99.0% R21 | **0.439 / 4.21× / 99.3% R21** |
| HAWE w8515 | 0.554 | ~0.435 |
| ws8 single | 0.419 | 0.273 |
| no_control | 0.110 | **0.104** |

**单一数字源**: `Multi-Agent VSGs/evaluation/paper_grade_axes.py` (post-fix patched) → 入口 `scripts/research_loop/eval_paper_spec_v2.py`.
**论文 paste 时主源**: `plan/evidence/EP-A2.md` (head 数字) + `EP-C5.md` (HAWE Asset 5).
**详情**: `CONTEXT.md` §11 + `RESEARCH_TRAIL.md` §4.6.

⚠ `plan/2026-05-07_*` 多份 sprint memo 数字仍 pre-fix, 已加头部 banner. 但仍要警惕直接 paste.

---

## 5.7 5 Bespoke Asset (rubric +++ 主战场)

dissertation §2.3 主战场, 必引 EP-C 系列:

1. **MCP Simulink toolkit** (Asset 1) — `EP-C1.md` (3300 LOC, 45 tools)
2. **Simulink RL bridge** (Asset 2) — `EP-C2.md` (1800 LOC bridge+env)
3. **TDD probe layer** (Asset 3) — `EP-C3.md` (760 LOC ANDES probe)
4. **6-axis evaluation framework** (Asset 4) — `EP-C4.md` (288 lines + post-fix patched)
5. **HAWE Heterogeneous Actor Weighted Ensemble** (Asset 5, v16 升级) ⭐ — `EP-C5.md` (~50 LOC inference, 99.3% R21 recovery)

⚠ v15 称 "ensemble" / "Phase 12 ensemble", v16 升 HAWE bespoke method 之一. 写时统一 "HAWE", 不混用 "ensemble".

---

## 6. Common Mistakes

- Citing a source without saying how it was used or adapted
- Qualitative description where a number is available
- Writing Introduction before the results are understood
- Presenting a figure without discussing what it shows or why
- No pass/fail criteria for specification points
- Unexplained unexpected results
- Overloaded paragraphs — break into subsections
- Missing units or inconsistent significant figures in tables/figures
- Weak section openers that skip stating the section's purpose
