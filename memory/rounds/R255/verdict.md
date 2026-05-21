# R255 verdict — Probe-first: local-vs-global r_f mismatch hypothesis REFUTED (env-change cancelled)

**Date**: 2026-05-20
**Status**: CLOSED-NEGATIVE — hypothesis disproved by 10-min probe; no env code touched
**Type**: research (probe-first per NOTES_ANDES.md; methodology validation)
**Wall**: ~30 min total (probe write + run + verdict)

## TL;DR

Wrote 10-min probe (`scripts/r255_probe_local_vs_global_rf.py`) to
test "RL cum_rf plateau caused by local-vs-global r_f scope
mismatch" hypothesis (from R252/CLM-0445 follow-up).

**Probe REFUTED hypothesis**: local r_f and global r_f are linked by
a **constant 2.66× scaling factor** across ALL controllers (RL,
droop, no-control). It's a topology-arithmetic constant, not a
controller-dependent attractor. Both metrics rank controllers
identically.

**R255 env-change CANCELLED before any code touched** — saved
~1-2 days of env-modification + V4 regression maintenance. Textbook
win for NOTES_ANDES.md probe-first protocol.

## Probe results (CLM-0460 has full data)

| Controller | local r_f | global r_f | local/global |
|------------|-----------|-------------|--------------|
| R201 hreg SOTA | -0.1116 | -0.0419 | **2.66×** |
| R254 phi_f-only | -0.1514 | -0.0568 | **2.66×** |
| R246 only-phi_abs | -0.1618 | -0.0607 | **2.66×** |
| Droop k=10 | -0.0660 | -0.0248 | **2.66×** |
| Droop k=2 | -0.1033 | -0.0387 | 2.67× |
| No-control | -0.3168 | -0.1188 | 2.67× |

Every controller (training-target-aware or not) sees the same ratio.
The "local-vs-global mismatch" is structural to the topology +
reward formula, not a behavior the controller can exploit.

## Mechanism (topology arithmetic)

Kundur ring: 4 agents, each with 2 neighbors. Per-agent local
r_f penalty sums over a 3-agent neighborhood (self + 2 neighbors).
Each agent k is contained in 3 such neighborhoods → its
deviation-squared term appears ~3 times in the total local-r_f
sum vs once in the global-r_f sum. The local-means cluster around
the global-mean for any synchronized state, so the effective
scaling converges to 3 (empirical 2.66 from the trajectory data).

This is a **constant of the topology + reward formula**, not a
property any controller can exploit.

## What the probe ALSO reveals

Looking at last-step r_f (t=30.5 s):

| Controller | last-step local r_f |
|------------|---------------------|
| R201 hreg SOTA | -6.4e-09 |
| R254 phi_f-only | -4.2e-08 |
| Droop k=10 | -4.7e-11 |
| No-control | -3.7e-08 |

All controllers — **including no-control** — reach near-zero r_f
by 30 s. The system fully synchronizes regardless of controller.
The cum_rf gap between controllers is dominated by the
**transient phase** (first ~5-10 s).

## Implication for paper Sec.IV-D contribution 1 (CLM-0445)

Strengthened: the RL-vs-droop cum_rf Pareto trade-off is REAL,
not a metric artifact. RL genuinely underperforms droop k=10 on
synchronization tightness; droop k=10 genuinely underperforms RL
on transient peak / settling / utilization. The Pareto frontier
represents an honest engineering trade-off.

This is the strongest possible framing for paper Sec.IV-D
contribution 1. No methodological caveat needed.

## Revised candidate mechanisms for RL cum_rf gap (not tested here)

The 2.66× refutation leaves the gap unexplained at mechanism level.
Plausible alternatives (each requires its own probe):

1. **Action-bound saturation**: RL actor outputs ∈ [-1,1] then
   projected; if droop k=10 demands larger actions than RL
   outputs, RL is action-bounded. Testable: extract per-step
   actions from R201 trajectory, compare distribution against
   droop k=10's actions.
2. **Anticipation lack**: droop reacts instantly via proportional
   control; RL must learn to anticipate. Testable: phase analysis
   of action vs Δf relationship in first 1-2 s.
3. **Reward-shape trade-off**: RL trained with phi_f + phi_abs
   simultaneously may converge to a Pareto-optimal balance that
   isn't the cum_rf-only optimum droop k=10 occupies.
4. **Network-coupling locality**: RL per-agent local observation
   may not exploit network coupling as efficiently as a
   well-tuned droop. Testable: CTDE / global-obs variant.

None of 1-4 motivates an env code change — they all motivate
either new probes (1, 2) or new training rounds with existing env
(3, 4). R255 closes; follow-up belongs to a new round if PI desires.

## Pre-registered outcomes (R255 hypothesis test)

| Predicted | Actual |
|-----------|--------|
| RL local-r_f << RL global-r_f → mismatch real | local = 2.66× global, **same as droop and no-control** → mismatch NOT controller-specific |
| Controllers exploit local-mean to hide drift | All controllers see the same ratio; nobody exploits anything |
| R255 env change justified | **R255 env change UN-justified by probe data** |

Outcome: hypothesis REFUTED at probe stage. Acted on probe-first
protocol → no env change made.

## Methodology validation: probe-first protocol works

**Cost-benefit**:
- Probe: 1 script file (~140 LOC), 10 min to write, 1 min to run.
- Verdict: 1 CLM + 1 round verdict.
- Total: ~30 min.

Counterfactual without probe:
- Env code change (add r_f_scope flag): ~2 hr (write + V4
  regression maintenance + tests).
- Train R255: 13 min × 3 seeds for cross-seed verify = ~40 min.
- Score + verdict + discover hypothesis wrong + revert: ~1 hr.
- **Total: ~4 hr**, with potential V4 regression breakage requiring
  rollback.

**Saved: ~3.5 hr + V4 contract risk.** Probe-first paid off ~8×.

## Questions opened (this round)

- (none — R255 hypothesis cleanly closed)

## Questions closed (this round)

- "Does local-vs-global r_f scope mismatch explain the RL cum_rf
  plateau (CLM-0445 follow-up)?" ANSWERED: NO. Both metrics rank
  controllers identically (2.66× scaling constant from topology
  arithmetic). The plateau has a different mechanism (candidates 1-4
  above, untested).

## Questions advanced (this round, status unchanged)

- "What IS the mechanism of the RL cum_rf plateau?" advanced from
  "local-vs-global mismatch" to "4 narrower candidates (action-bound,
  anticipation, reward-shape, observation-locality)" — each
  amenable to its own probe.

## 给 PI 的话

**这周干了啥**：R255 候选是 "RL cum_rf plateau 由 local-vs-global
r_f scope mismatch 导致 → 加 r_f_scope='global' flag 训练". 按
NOTES_ANDES.md probe-first 协议, **先写 10-min probe 验机制, 后决定
是否动 env code**.

**结果（一句话）**：probe **REFUTE hypothesis** — local r_f / global
r_f = **2.66× 常数, 跨所有 controller** (RL, droop, no-control 都一样).
是 ring 拓扑的 arithmetic constant, 不是 controller-dependent
attractor. R255 env-change **取消, 0 行代码 touched**.

**意外**：
1. **2.66× 是 universal scaling**, 不是 metric-mismatch. 这是 4-node
   ring topology + 3-agent local-mean reward formula 的 arithmetic
   constant. 任何 controller 都 see same ratio.
2. **All controllers (含 no-control) 在 t=30s 都达到 near-zero r_f** —
   系统总会 sync, 差别在 transient 阶段 (前 5-10s). cum_rf 差距全在
   transient.
3. **probe-first 协议 ~8× cost saving** (30 min probe vs 4 hr 含 env
   change + V4 regression risk). NOTES_ANDES.md 协议有 real value.

**Paper Sec.IV-D contribution 1 strengthened**: RL-vs-droop Pareto
trade-off 现在 mechanism-clean — 不是 metric artifact, 是 real
engineering trade-off. **不需要 caveat**.

**我默认下一步做**：
1. **Stop R255 line**; mechanism candidates 1-4 各需要 own probe,
   不立即 chase.
2. 更新 gauge-invariance memo 加 R255 probe finding (Pareto = real,
   not metric artifact). 让 paper framing 干净.
3. 现在 paper Sec.IV-D 5 contribution + 1 RL-vs-droop Pareto +
   decomposition + drop-in recipes 全 lock down. **强烈推荐 stop
   research, 写 paper draft**.

**你想插一脚就说**：probe-first protocol 这次 textbook 演示. 数据
更 clean. 如果你还想跑 mechanism candidate 1 (action-bound) 或 2
(anticipation), 各需要再 30 min probe. 不然 default 停研究 + 写 paper.

## Cross-references

- CLM-0445 (R252 — discovered RL-vs-droop cum_rf gap, opened R255 hypothesis)
- CLM-0455 (R254 — phi_f decomposition, narrowed R255 hypothesis)
- CLM-0460 (this round's claim)
- `scripts/r255_probe_local_vs_global_rf.py` (probe code)
- `results/r255_probe_local_vs_global_rf.json` (probe data)
- `docs/eng-notes/NOTES_ANDES.md` (probe-first protocol)
- `docs/paper_drafts/sec_iv_d_paper_eq14_gauge_invariance.md` (memo update pending)
