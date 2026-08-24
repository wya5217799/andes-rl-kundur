# ICEMS 2026 acceptance assessment for a negative-result paper

**Research value: moderate** -- Official venue and IEEE review standards support a bounded qualitative judgment, and an official ICEMS 2023 report supplies one historical overall acceptance rate; ICEMS 2026 still publishes neither a current rate nor a negative-results policy from which a manuscript-specific probability could be calculated.

**Checked:** 2026-08-25 (UTC+8)

**Manuscript:** *Decoupling-Oriented Coordination of Paralleled VSGs With Multi-Agent Reinforcement Learning*

## Bottom line

ICEMS does not appear to exclude scientifically valid negative results, but there is no evidence that it gives them extra tolerance. For this manuscript, acceptance is **not safely describable as likely** merely because the corrected direct-M/D formulation still fails. The realistic assessment is:

- **Execution-valid, non-trivial, mechanism-informative negative result:** conditionally publishable; the result must still clear originality, technical depth, correctness, contribution, and readability.
- **A proposed method merely fails to outperform a baseline:** acceptance prospects are probably **low** unless the paper establishes a useful failure boundary or refutes a technically important hypothesis.
- **A failure caused by a known execution or implementation mistake:** not a scientific negative result and materially harms acceptance prospects until it is isolated and the corrected object is independently revalidated.

Therefore, the earlier M/D mistake does **not** make reviewers more permissive. Its only potentially useful role is to create a transparent correction narrative; the publishable evidence begins with the corrected, valid experiments, not with the invalid runs.

## What the official criteria actually require

ICEMS 2026 asks the one-page digest to explain the problem, key results, and unique contributions. Its listed topics include Grid-Forming Technologies, Smart Grids and Microgrids, and AI for Electrical Drives and Energy Systems, so the subject is in scope. The regular route is digest review followed by a 4--6-page final manuscript after digest acceptance. ([ICEMS 2026 home/CFP](https://www.icems2026.org/), [digest submission](https://www.icems2026.org/digest-submission/), [full-paper submission](https://www.icems2026.org/full-paper-submission/))

The most explicit public ICEMS 2026 review rubric states that submissions are evaluated for **originality, technical/research content and depth, correctness, relevance, contribution, and readability**. It does not require a positive effect, but it also contains no negative-result track or waiver of those criteria. ([ICEMS 2026 special-session call](https://www.icems2026.org/call-for-special-sessions/))

IEEE's official conference peer-review guidance similarly asks whether the study is well designed and executed, whether data are correctly reported, analyzed, and interpreted, and whether the work advances the field. That makes validity and contribution decisive, not the sign of the result. ([IEEE Conference Author Center: peer review](https://conferences.ieeeauthorcenter.ieee.org/understand-peer-review/))

As supporting but **non-ICEMS** evidence, IEEE Access explicitly recognizes a `Negative Result` article type when the question is meaningful, the result is non-trivial, and the study is rigorous. This shows that a negative outcome is not inherently unpublishable in the IEEE ecosystem, but it cannot be used to infer an ICEMS acceptance advantage. ([IEEE Access submission checklist, p. 2](https://ieeeaccess.ieee.org/wp-content/uploads/2025/09/IEEE-Access-Submission-Checklist.pdf))

## Acceptance-rate evidence

An official China Electrotechnical Society report for **ICEMS 2023** states that the conference received 1,501 submissions and accepted 993 full papers, an overall acceptance rate of **66%**, after review by more than 500 experts. This is credible evidence that at least that edition was not an ultra-low-acceptance venue. It is only a 2023 conference-wide baseline: it is not an ICEMS 2026 rate, not a rate for the AI/grid-forming track, and not a negative-result-paper acceptance rate. ([China Electrotechnical Society ICEMS 2023 conference report](https://www.ces.org.cn/html/report/23111750-1.htm))

No official ICEMS 2026 source located in this search reports its numbers submitted, accepted, or current acceptance rate. A 2026 percentage, or a percentage specific to negative results, would therefore be invented rather than evidence based.

A bounded search of IEEE Xplore and author-hosted copies from ICEMS 2021--2025 did not locate a recent ICEMS paper that could be confirmed as a **pure, headline negative-result paper**. One accepted ICEMS 2021 paper, *Generative Adversarial Networks for Localized Vibrotactile Feedback in Haptic Surfaces*, openly reports that one investigated model did not reproduce the desired time-domain waveform/frequency content, but the paper retained a broader positive feasibility contribution. This is evidence that limitations can be reported inside an ICEMS paper, not evidence that ICEMS preferentially accepts negative-result papers. ([IEEE DOI record](https://doi.org/10.23919/ICEMS52562.2021.9634513), [author-hosted record/full text](https://infoscience.epfl.ch/entities/publication/72204da9-8ef9-4a94-8aa7-a65b9621c074))

## Scientific negative result versus execution mistake

| Situation | Scientific status | ICEMS implication |
|---|---|---|
| Run is affected by wrong units, conversion, diagnostics, or incomplete execution | Invalid for efficacy inference | Must be quarantined; it cannot support either success or failure |
| Error is fixed, invariants pass, corrected experiments are independently executed, and the method still fails frozen gates | Valid bounded negative result | Potentially publishable if the failure is non-trivial and informative |
| Corrected method does not beat a baseline but no mechanism or useful boundary is established | Weak negative result | Likely viewed as insufficient contribution |
| Corrected study identifies a reproducible failure mechanism, invalidates an important assumption, or defines where a popular formulation cannot work | Failure-mode or formulation-limit contribution | Strongest negative-result positioning |

An execution mistake can become part of a contribution only if the mistake exposes a general, previously unrecognized, reproducible engineering failure mode and the paper includes a clean corrected comparison. That is a methods/failure-analysis contribution; it is not reviewer tolerance for erroneous evidence.

## Manuscript-specific assessment

The current repo evidence contains a defensible separation:

- R478 reports that the corrected one-convention M/D implementation passes all seven post-fix invariants and re-locks the V4 regression. Its three sealed energy-port families then fail every registered decoupling gate, with guards and integrity checks passing. This is a **valid formulation-limiting result**, not an execution-error result. ([R478 feed](../reports/R478.md))
- R457 is another valid bounded refutation: an output-preserving common-head repair leaves the actors responsive but does not produce the registered critic, calibration, mediation, or physical benefit. It supports a specific causal failure statement, not a universal claim against MARL or critics. ([R457 feed](../reports/R457.md))
- Any earlier object invalidated by diagnostic or M/D semantics must remain excluded from efficacy claims. It can motivate the correction, but it must not be pooled with the corrected numbers.

This gives the paper more than “the method failed”: it can say that a physically corrected direct-M/D formulation and a targeted learning-side repair were tested under explicit gates, yet neither restored the required closed-loop physical response. The contribution is the **failure boundary and causal narrowing**. The claim must remain limited to the registered modified-Kundur setup, fixed connectivity/banks, action formulation, information pattern, and tested repair budgets.

The fixed title creates a presentation risk because readers may naturally expect successful coordination. Without changing the title, the abstract and introduction should make clear that “decoupling-oriented coordination” names the investigated formulation, not an achieved performance result. The paper should not imply that direct-M/D control, MARL, topology generalization, stability, or deployment has been validated.

## Practical probability judgment

Because ICEMS 2026 publishes no current acceptance statistics and no policy by result sign, a manuscript-specific numerical probability is not supportable. The 66% overall rate reported for ICEMS 2023 suggests that the venue as a whole has historically offered reasonable acceptance chances to sound, in-scope work, but it does not show that a negative-result manuscript enjoys the same rate. The best evidence-bounded judgment is:

- **Submitted as a success-style MARL paper whose main method fails:** low acceptance prospect.
- **Submitted as a rigorous, transparent formulation-limit/failure-mechanism paper:** a **moderate, genuinely contestable prospect**, but not “high probability” on the evidence available. The strongest ingredients are the corrected invariants, frozen gates, independent-bank failures, causal interventions, and narrow claim ceiling.
- **Submitted using invalid runs or treating the earlier mistake as an excuse:** very poor scientific defensibility.

If the one-page digest is already accepted, the ordinary competitive digest decision has already occurred; the immediate risk shifts to whether the final 4--6-page paper remains truthful, technically sound, and consistent with the accepted digest. A material reversal from a success claim in the accepted digest to a negative final result should not be hidden. The accepted digest and decision letter should be checked before finalization, and the ICEMS secretariat should be asked if the change materially alters the accepted contribution.

## Recommended paper posture

1. Lead with the meaningful question and the corrected scientific object, not the history of failed runs.
2. State the negative result as a bounded falsification: the tested corrected direct-M/D candidate did not establish the registered decoupling/physical benefit.
3. Show why the null result is informative: unit/convention correction, invariant proof, strong comparator, pre-registered gates, causal interventions, integrity checks, and explicit limits.
4. Keep invalid runs in a short internal-validity disclosure; do not count them as evidence or pool their values.
5. Avoid universal language such as “MARL does not work,” “M/D decoupling is impossible,” or “critic repair is ineffective.”

## Sources used

- [ICEMS 2026 official website and call for papers](https://www.icems2026.org/) -- venue scope, digest-to-full-paper route, key-results and contribution expectations.
- [ICEMS 2026 digest submission](https://www.icems2026.org/digest-submission/) -- official initial-submission and acceptance workflow.
- [ICEMS 2026 full-paper submission](https://www.icems2026.org/full-paper-submission/) -- final-paper length and camera-ready workflow.
- [ICEMS 2026 special-session call](https://www.icems2026.org/call-for-special-sessions/) -- conference's public evaluation criteria.
- [China Electrotechnical Society ICEMS 2023 conference report](https://www.ces.org.cn/html/report/23111750-1.htm) -- official historical count: 1,501 submissions, 993 accepted full papers, 66% overall acceptance.
- [IEEE Conference Author Center: Understand Peer Review](https://conferences.ieeeauthorcenter.ieee.org/understand-peer-review/) -- official validity, data, novelty, clarity, scope, compliance, and advancement criteria.
- [IEEE Conference Proceedings: Guide to Scope and Quality Criteria](https://events.ieee.org/wp-content/uploads/conference-scope-and-quality-criteria.pdf) -- reproducible methods, tested hypotheses, reported data, interpretation, and conclusions.
- [IEEE Access submission checklist](https://ieeeaccess.ieee.org/wp-content/uploads/2025/09/IEEE-Access-Submission-Checklist.pdf) -- explicit negative-result category, used only as adjacent IEEE policy.
- [Hernandez Mejia et al., ICEMS 2021](https://doi.org/10.23919/ICEMS52562.2021.9634513) -- accepted ICEMS example that reports a model limitation within a broader feasibility paper.
