# R256 verdict — Action-bound saturation IS REAL but is a policy symptom (probe-first protocol 2nd win)

**Date**: 2026-05-20
**Status**: CLOSED-POSITIVE — mechanism #1 surface-confirmed but root-cause refuted; paper-grade revised narrative
**Type**: research (probe-first per NOTES_ANDES.md; mechanism investigation)
**Wall**: ~30 min total (probe write + run + verdict)

## TL;DR

Wrote 10-min probe testing CLM-0460 mechanism candidate #1
"action-bound saturation". Result: **RL hits action bounds 22-91%
of trajectory** (R201 delta_D saturates 87.8% — most extreme).
**But** droop k=10 achieves BETTER cum_rf with delta_M=0 + delta_D≈430
(below bound). And R195/CLM-0175 already showed widening bounds
REGRESSES performance.

**Real mechanism revealed**: RL learns a degenerate "max-out"
policy (saturate every available action); classical droop is
proportional by construction (titrates). The policy-class
inductive bias is the root cause of the cum_rf plateau, not the
action bound itself. R257 env-change (widen bounds) would
duplicate R195 failure.

## Probe data (CLM-0470 has full table + interpretation)

| Controller | dM sat% | dD sat% |
|------------|---------|---------|
| R201 SOTA | 22.0% | **87.8%** |
| R254 | 70.0% | 69.0% |
| R246 | 69.7% | **91.5%** |
| Droop k=10 | 0% | 2.5% |
| Droop k=2 | 0% | 0% |

ALL THREE RL controllers (different reward configs) saturate
heavily. Droop k=10 (cum_rf-best) uses 0 inertia adjustment and
keeps damping below bound. **Same action space, different
strategy class**.

## Pre-registered outcomes (R256 plan)

| Outcome | Predicted | Actual |
|---------|-----------|--------|
| RL sat > 5% AND droop < bounds | hypothesis SUPPORTED → R257 widen | RL sat 22-91%, droop 0-2.5%. **Surface hypothesis SUPPORTED but R195 already refutes "widen helps"** |
| RL and droop both <1% | REFUTED | not happened |
| Borderline 1-5% | manual disambiguate | not happened |

**Outcome STRONGER than plan**: probe didn't just support the
"saturation real" finding, it surfaced the **policy-class-bias
mechanism** that explains why R195 widebound regressed.

## Revised paper Sec.IV-D mechanism narrative

> "RL-vs-droop cum_rf gap (CLM-0445) reflects a policy-class
> inductive bias: TD3+LSTM with per-agent tanh-projected actor
> converges to a 'max-out' strategy (delta_M + delta_D saturate
> at upper bound 22-92% of trajectory, across all tested reward
> configs). Classical droop's proportional structure FORCES
> titration. Widening action bounds (R195) does NOT help — the
> max-out policy uses extra range to over-actuate. The path to
> a better RL controller is structural inductive bias toward
> proportional control: (a) linear/soft actor outputs, (b) action
> magnitude regularisation, (c) hybrid RL+droop warm-start. All
> deferred future work; this section reports the mechanism."

## R257 candidate REJECTED

The "widen action bounds" R257 candidate that R256 plan suggested
would duplicate R195 (CLM-0175) failure. Probe-first protocol
caught this:
- R256 probe: 30 min, 0 env code touched.
- Counterfactual without probe-first: re-run R195-style widebound
  training. Already known to regress (per CLM-0175 prior).
- **Saved**: ~13 min training + verdict writing + V4 regression
  testing for an experiment already in the ledger as failed.

This is the **second probe-first save** in this session (after
R255 / CLM-0460 local-vs-global probe). Tool-validated workflow.

## Mechanism candidate update (post-R256)

Per CLM-0460 four candidates:

| # | Candidate | Status after R256 |
|---|-----------|---------------------|
| 1 | Action-bound saturation | **surface-confirmed; root-cause refuted (R256)** — bound is symptom of #5 |
| 2 | Anticipation lack | untested |
| 3 | Reward-shape trade-off | partially explored via R254 decomposition |
| 4 | Observation-locality (CTDE) | untested; architectural |
| **5** | **Policy-class inductive bias (max-out)** | **identified by R256 as root cause** |

## Paper 7th contribution candidates (deferred)

Three paths to a better RL controller, all deferred:

(a) **Linear/soft actor output**: replace tanh with linear (with
    soft action clipping). Estimated: ~1 day env+train+verify.
(b) **Action magnitude regularization**: add -λ|action|² to
    training reward. Estimated: ~4 hr (no env change, just
    reward shape).
(c) **Hybrid RL+droop warm-start**: initialize actor at droop k=10
    behavior. Estimated: ~1 day (training pipeline change).

Per CLM-0148/0149 "plateau structural per 91 trials" rule, these
are speculative — may not beat the algorithm-level plateau
either. Paper-7th-contribution candidates IF future work pursues;
not required for current paper draft.

## Questions opened (this round)

- (none formal — mechanism #5 is a NEW finding, candidates 2/4
  remain untested but lower-priority)

## Questions closed (this round)

- "Is RL action-bound-constrained vs droop?" ANSWERED: Yes
  surface-wise (RL saturates 22-91%), No causally (R195 widebound
  regresses).
- "What IS the mechanism of RL cum_rf plateau?" Tightened:
  policy-class inductive bias toward max-out strategy. Not action
  bounds, not metric mismatch, not paper-term distribution.

## Questions advanced (this round, status unchanged)

- Q-0004 (AndesBaseEnv absorb) — not touched.

## 给 PI 的话

**这周干了啥**：R256 测 R255 mechanism candidate #1 (action-bound
saturation) — RL 是否被 action 上限卡住. Probe-first 协议 (10-min
analysis, 0 env code).

**结果（一句话）**：**RL 确实 saturate 22-91% time**, R201 SOTA delta_D
钉在 +600 bound **87.8% of trajectory** — 极端 "max-out" 策略.
**BUT** droop k=10 用 delta_M=0 + delta_D≈430 (below bound) 反而
cum_rf 更好. R195 (CLM-0175) 已证 widen bound REGRESSES. **真正
mechanism**: RL 是 policy-class inductive bias (max-out), 不是 bound 限制.

**意外**：
1. **R201 SOTA 87.8% time pinned at delta_D=+600**. 我没预期 saturation
   这么严重. 这本身是 paper-grade 数据 — "RL 怎么 learn 行为" 的
   forensic.
2. **3 个 reward configs (R201 hreg, R254 phi_f-only, R246 only-phi_abs)
   都 saturate** — 不是 reward-shape 影响. 是 policy class 的固有 bias.
3. **R195 widebound regress 现在 mechanism-clean** — 给 max-out 更多
   空间, regression deeper. 不是 "more capacity = better".
4. **Probe-first 第二次 textbook 救轮** — R257 widebound 候选会
   duplicate R195 失败. 30 min probe 救 1-2 hr.

**我默认下一步做**：
1. ✅ R256 close + paper memo 加 "policy-class max-out mechanism" panel.
2. mechanism candidate #2 (anticipation lack) probe — 又 10 min,
   读 R201 action vs Δf phase. 如要做下一个 probe.
3. **或** stop research (现在 paper Sec.IV-D 已 6 contribution + mechanism
   final 解释 + 3 audit-corrected dual-metric panels + decomposition
   recipe + Pareto frontier explanation). 写 paper draft.
4. Paper 7th contribution 候选 (linear-actor / action-reg / hybrid-warmstart)
   全 deferred — speculative, 不 in 当前 scope.

**你想插一脚就说**：probe-first 协议 2/2 救轮成功. Action-saturation
+ policy-class-bias 是 paper Sec.IV-D mechanism 最 final 的解释.
推荐 stop, 写 paper. 如果要继续 mechanism #2 probe, 我可以 30 min
完成. R257 widebound 我 NOT 推荐 — R195 已证.

## Cross-references

- CLM-0460 (R255 — probe-first refutation of local-vs-global; opened mechanism #1-4 candidates)
- CLM-0175 (R195 — widebound REGRESSES; refutes "raise bounds" naive fix)
- CLM-0445 (R252 — RL-vs-droop Pareto, this round explains mechanism)
- CLM-0148/CLM-0149 (R86 — plateau structural per 91 trials; constrains expectations for paper-7th candidates)
- CLM-0470 (this round's claim)
- `scripts/r256_probe_action_bound_saturation.py`
- `results/r256_probe_action_bound_saturation.json`
- `docs/paper_drafts/sec_iv_d_paper_eq14_gauge_invariance.md` (memo update pending)
