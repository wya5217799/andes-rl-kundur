---
round: R92
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R92 plan — Multi-agent action-coordination diagnostics, zero ANDES

**Status**: ACTIVE
**Opened**: 2026-05-19
**Driver**: PI "继续研究". R87 (CLM-0165) closed R84-W2/W3 affine-Q
interpretation; per-agent Q1/Q2 disagreement spread 14× (agent_1=0.003 vs
agent_0=0.043) flagged but action-side coordination was never analysed.
R88-R91 already reserved by other sessions; R92 is the next free.
**Parent**: R87 / CLM-0165 (agent_1 epistemic outlier flag), CLM-0123
(R72_w4 P_balance=0.96 paper headline).

## TL;DR

Reuse `results/r84_d2b_q_landscape_trajectory/per_step.json`'s
`sota_action[i] = [ΔM_norm, ΔD_norm]` across 4 agents × 2 scen × 50 step =
400 sota_action vectors. Question: do the 4 agents coordinate effectively,
or is the 0.391 plateau partly explained by **action-side** structure
(redundancy, antagonism, specialisation imbalance) that single-agent RL
naturally can't escape? Multi-agent CTDE was an R82-verdict option (b)
but R82 chose algo path instead — R92 surfaces whether that was
the right call **using data that already exists**, before any new training.

Zero ANDES, zero training, zero ckpt mutation. Wall ~30 min.

## Background — what is already established

- **R72_w4 SOTA P_balance axis = 0.96** (CLM-0123): in 6-axis canonical
  ranking the action effort is *globally* well balanced.
- **R87 per-agent Q1/Q2 disagreement spread 14×** (CLM-0165): agent_1
  critic is unusually confident; rest of agents normal. Could be a
  side effect of agent_1's action distribution.
- **R82-(b) multi-agent CTDE candidate** (R82 verdict): "工程量大但
  setup-level novel"; PI sentinel for "structural" reformulation. Not
  pursued yet.

R92 doesn't make new training claims; it gives a data-driven verdict on
whether the **action structure** is suspect enough to warrant the CTDE
investment.

## Wave 1 (W1) — Action structure characterisation

Inputs: per_step.json `sota_action` 2-D vectors per (scenario, step, agent).

Six analyses:

### Axis A. Per-agent action effort (ΔM_norm + ΔD_norm magnitudes)

For each (agent, scenario): mean / std / percentile of |ΔM_norm|, |ΔD_norm|,
and L2 norm. If one agent does 50%+ of total effort, action assignment
is uneven → CTDE / role-aware design has a target.

### Axis B. Inter-agent action correlation

For each scenario × action-component (ΔM or ΔD), build a 4 × 4 Pearson
correlation matrix of agents' trajectories. Cases of interest:
- All-positive correlation > 0.8 → agents are **redundant** (move in lockstep)
- Strong negative pairs → **antagonistic** (one agent compensates another)
- Near-zero off-diagonal → **independent** (clean specialisation)

### Axis C. Time-series visualization

4 agents × 2 scen × 2 action components = 16 curves on 4 subplots.
Mark impulse / rising / decaying / settling phases. Eye-check whether
all agents activate simultaneously or sequentially.

### Axis D. ΔM vs ΔD specialisation per agent

For each agent: ratio of `|ΔM_norm|` total magnitude to `|ΔD_norm|`
total magnitude. If agent_i always emits ΔM > ΔD and agent_j the
reverse, that's emergent role specialisation. If all agents balanced
50/50, no specialisation.

### Axis E. Action saturation frequency

Fraction of steps where `|action[k]| > 0.95` (near boundary). Per
agent, per action dim. High saturation = clipping → policy can't
express finer control → could be a hidden bottleneck.

### Axis F. Cross-scenario role consistency

For each agent: is the role learned in LS1 the same as in LS2? Compare
Axis-A effort ranks and Axis-D specialisation ratios across the two
scenarios. Low consistency → agents are scenario-specific (less
generalisable, possibly fragile to disturbance variation).

## Gate criteria (R92 closure)

- **STRUCTURAL** (any of):
  - one agent does ≥ 50% of total effort (Axis A)
  - any pair has |corr| > 0.8 (Axis B) → redundancy/antagonism
  - saturation > 30% on any (agent, dim) (Axis E)
  - role consistency Δ > 50% across LS1 vs LS2 (Axis F)
  → mechanism candidate: action structure is suspect, CTDE / role-aware
    reformulation justified at R93+

- **BALANCED** (none of the above triggers):
  → action structure is clean; agents already coordinate adequately.
    CTDE investment unlikely to help. R93+ stays on D3 obs sufficiency
    / D4 env floor / reward-shape.

## 资产保护契约

不动 V4 / V4Config / base_env / paper_grade_axes / agents/ / R57+ ckpt.
新建: `scripts/r92_w1_action_coord.py`, `results/r92_w1_action_coord/`
(summary.json + 2 figures + csv tables), `memory/rounds/R92/verdict.md`,
1 CLM (≥ CLM-0166 to dodge in-flight races).

## Cross-references

- CLM-0123 (P_balance=0.96 — paper-level effort balance metric; R92 axis-A is
  per-(scen,agent) breakdown of the same quantity)
- CLM-0165 / R87 (agent_1 epistemic outlier; W1 axis-B/D may explain)
- R82 verdict option (b) multi-agent CTDE — R92 is the "should we?" data
- CLM-0160 (per_step.json data origin)
