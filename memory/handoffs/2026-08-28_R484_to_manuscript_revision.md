# Handoff: R484 closeout to evidence-bounded conference manuscript revision

## Handoff card

- Current owner: R484 closeout task.
- Required input: commit `6d52507bd2580af132e56a3fe7251b7c615a1215`,
  `memory/claims/CLM-1520.md`, and
  `paper/yang_md_decoupling_marl/reports/R484.md`.
- Acceptance check: `session_context.py --json --line
  yang-md-decoupling-marl` reports manuscript mode, stage
  `evidence-bounded-manuscript-revision`, no active round, no artifact alert,
  and CLM-1520 in `evidence_refs`.
- Authority and write scope: manuscript work under
  `paper/yang_md_decoupling_marl/`; R483/R484 formal evidence is read-only.
  No experiment, training, tuning, retry, threshold change, or new scientific
  claim is authorized.
- Return artifact: an evidence-bounded ICEMS 2026 conference draft whose
  abstract, results, figures, discussion, conclusion, and evidence map agree
  with CLM-1520 and the R484 feed.
- Return verification: manuscript evidence audit, domain audit, LaTeX build,
  PDF visual check, feed/claim locator check, and submission-requirements check.
- Next owner: the new manuscript-revision Codex task created from this handoff.
- Stop condition: the revised conference draft is reviewed and contains no
  frozen-policy family-wide, probability, topology, safety, stability,
  hardware, deployment, zero-effect, or equivalence overclaim.

## Verified current state

- R484 is formally completed and committed at `6d52507`.
- Formal result integrity: 16/16 shards, 848/848 blocks, and 5,088/5,088
  trajectories; all required sidecars and manifest checks passed.
- None of the 208 frozen R483 policies passed the registered 30-second complete
  relative physical/action guard. Although 126/208 met both aggregate 5%
  endpoint targets, all 832/832 policy-profile blocks exceeded both registered
  relative action-stress limits.
- Frozen direct M/D separately passed the registered fresh-bank gate on 4/4
  profiles. Canary and fresh banks, and the R483 6-second and R484 30-second
  analyses, remain non-pooled.
- No 30-second source-factor effect established improvement above the 10%
  materiality boundary after Holm control. The actor-by-critic estimate remains
  descriptive, not confirmatory.
- Publication gate: evidence audit PASS, domain audit PASS, external context
  NOT-APPLICABLE, disposition QUALIFY.
- R484 targeted tests passed 20/20. The full WSL suite reported 2686 passed and
  22 scope-external historical/runtime failures; none is owned by R484.
- Existing unrelated untracked files must remain untouched: `.codex/`,
  `memory/notes/NOTE-0035.md`, `memory/notes/NOTE-0036.md`, and the three
  scratch scripts shown by `git status --short`.

## Manuscript decision

The old narrative that learning control is generally superior is not
supportable. The defensible conference-paper story is narrower: within the
sealed one-topology tested bank, many frozen learned policies improve the two
aggregate response endpoints, but none satisfies the complete relative
physical/action contract because action stress is consistently too high; the
frozen deterministic reference passes its separate fresh 30-second gate.

The next task should revise the paper before considering any additional
experiment or mathematical package. Keep the fixed title exactly as written in
`paper/yang_md_decoupling_marl/LINE.md` unless the owner explicitly changes it.

## 给 PI 的话

**发生了什么**：三十秒补充评价已经完整通过数据和完整性检查。所有学习控制方案都没有通过事先约定的完整要求：不少方案确实改善了两项响应指标，但每个测试工况的控制动作强度和变化量都超过了事先允许的相对范围。作为参照的方法则在全部新测试工况中通过。

**这说明什么**：原来“学习控制整体更优”的论文叙事不能成立。现有证据支持一个更窄但清楚的结论：这些固定学习方案存在响应改善与控制动作代价之间的冲突，而参照方法在同一套三十秒要求下更稳妥。这个结果只针对当前系统和测试工况，不能推广成所有学习方法都失败。

**下一步做什么**：停止补实验和调参，立即把论文改成受证据约束的会议稿。结果部分保留动作代价冲突和参照方法通过的事实，摘要和结论删除学习方法普遍优越的表述；随后只做论文重写、图表更新和投稿检查。

## Redaction

No credentials, API keys, or private tokens are included.
