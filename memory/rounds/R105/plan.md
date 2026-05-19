---
round: R105
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R105 plan — Reward function audit: project vs paper Eq.14-18 verbatim

**Status**: ACTIVE (audit-only, zero compute)
**Opened**: 2026-05-19
**Driver**: While R102 runs in WSL background (~25 min), use Windows-side time for high-ROI zero-conflict audit. Following R89's "audit ANDES Kundur vs paper physics" pattern, audit the **reward function** — if R57-R85 trained on a fundamentally different reward than paper Eq.14-18, then "RL > classical" comparisons in CLM-0184/0186 land on a quantitatively different objective than paper's DDIC.
**Parent**: CLM-0094 (R72_w4 SOTA); paper §III-A reward Eq.14-18; `docs/paper/kd_4agent_paper_facts.md` §2.4.

## TL;DR

R72_w4 SOTA `training_log.json::env_config` shows training-time reward
weights **diverge substantively from paper Eq.14**:

| Component | Paper Eq.14 | R72_w4 SOTA training | Δ |
|---|---|---|---|
| φ_f (sync) | 100 | 100 | match ✓ |
| φ_h (ΔH penalty) | **1** | **0.0056** | **÷178** |
| φ_d (ΔD penalty) | **1** | **0.0056** | **÷178** |
| φ_abs (Δω² restore) | **(not in paper)** | **50** | **+50% of φ_f** |
| action_penalty_mode | physical (paper Eq.17-18) | normalized | rescale by DM_MAX |
| h_paper_interpretation | mechanical_H (paper default) | mechanical_H | match ✓ |

**Interpretation**:
- Paper trains on: synchronization + action-smoothness
- R72_w4 trains on: synchronization + **frequency restoration** (r_abs) + essentially-zero action penalty
- The two objectives push the policy in DIFFERENT directions:
  - Paper: minimize sync error; if all 4 agents flat-deviate together, r^f=0 even with Δf≠0
  - R72_w4: minimize sync AND minimize |Δω| absolute; freq must return to nominal

R57-R85 SOTA claims (CLM-0094 / CLM-0186) compare R72_w4 vs droop on
`paper_grade_axes` 11-axis (paper-style metrics like max_df, settling), but
the SOTA was OPTIMIZED for restoration not just synchronization. R85's
"1.99× advantage over droop" is therefore "RL trained on augmented reward
> classical droop with paper-style eval" — a defensible but non-trivial
caveat for paper write-up.

## Methodology (audit, no compute)

1. Read `src/andes_rl_kundur/env/andes/base_env.py:586-730` (_compute_rewards) verbatim
2. Compare term-by-term with paper Eq.14-18 (canonical in
   `docs/paper/kd_4agent_paper_facts.md` §2.4)
3. Read `results/r72_w4_lstm_tau001_warmup5_s54/training_log.json::env_config`
   to lock R72_w4 SOTA training-time reward weights
4. Cross-ref `src/andes_rl_kundur/env/andes/v4_config.py::V4Config.paper_strict_pure`
   to confirm an alternative exists (phi_abs=0, phi_h=phi_d=1)
5. Document 2-3 findings as claims

No script needed (pure file inspection + JSON read). No conflict with R83/R85/R102.

## Findings

### F1 (CRITICAL): r_abs term NOT in paper Eq.14, weighted 50% of r_f

`base_env.py:684,709,711`:
```python
r_abs = -(float(d_omega[i])) ** 2    # NON-paper term
rewards[i] = self.PHI_F * r_f + self.PHI_ABS * r_abs + self.PHI_H * r_h + self.PHI_D * r_d
```
Code comment line 79-84: "BackendProfile (ANDES-family augmentation):
PHI_ABS adds an absolute frequency... 解决 Kundur 紧耦合问题".

`V4Config.phi_abs default = 50.0`. Only `V4Config.paper_strict_pure()` and
`paper_strict_rescaled()` set `phi_abs=0.0`. R72_w4 used default → phi_abs=50.0.

R72_w4 trained on: 100·r_f + 50·r_abs (+ tiny r_h/r_d). r_abs pushes Δω→0
(frequency restoration), but paper §2.4.2 explicitly states r^f=0 even
when all 4 agents flat-deviate together (no restoration requirement).

### F2 (HIGH): φ_h, φ_d ÷178 vs paper

Paper Sec.IV-B verbatim: `φ_h=1, φ_d=1`.
R72_w4 trained: `phi_h=0.0056, phi_d=0.0056` ≈ 1/178.

Likely rationale (from R18 historical, archived script
`scripts/_archive/r20_reward_settled_audit.py`): with `action_penalty_mode=normalized`
the ΔH avg is in [-1,1], squared in [0,1]. Paper might assume physical
ΔH (range [-100, 300]) where r_h = -(150)² = -22500 dominates everything
unless φ_h=1/22500. ÷178 is empirically tuned to balance r_f at training scale.

Net effect: action smoothness is **essentially unweighted** in R72_w4
training. Paper's "control objective 2: 系统总惯量+阻尼基本不变" (paper
§0.5, double-objective) is effectively NOT enforced in R72_w4 training.

### F3 (MEDIUM): action_penalty_mode = normalized (paper says physical)

Paper Eq.17 reads as $r^h = -(\Delta H_{avg})^2$ with ΔH in physical units (paper
§13 Q-A admits H dimensionality is unclear). R72_w4 uses `normalized` mode
which divides by `max(DM_MAX, |DM_MIN|)=300`. So R72_w4's r_h is on a
different scale than paper's literal reading.

### Aggregate

R72_w4 training-reward layout (effective contribution magnitudes for typical state):

```
component        | weight | typical mag | contribution
r_f (sync)       |  100   |   0.001     |  -0.1
r_abs (restore)  |   50   |   0.005     |  -0.25   ← biggest!
r_h (norm. ΔH²)  |  0.0056|   0.04      |  -0.0002
r_d (norm. ΔD²)  |  0.0056|   0.04      |  -0.0002
```

**Dominant signal during early training is r_abs (frequency restoration), not r_f (paper's sync)**. R72_w4 is essentially a "restore-the-frequency" agent with synchronization as a secondary objective.

## Claims to write

- CLM-NEW1 (F1+F2 aggregate): R72_w4 SOTA training reward divergence from paper Eq.14
- CLM-NEW2: 量化 effective reward contribution + interpretation (R72_w4 trained as restoration-agent not pure-sync agent)

## Cross-references

- CLM-0094 (R72_w4 SOTA) — eval geo conditional on training reward
- CLM-0184/0186 (R85 droop baseline) — comparison apples-to-apples on eval metric (paper_grade_axes), but training objectives differ
- CLM-0149 (R84 actor-critic decoupling on SOTA critic) — critic learned on the AUGMENTED reward
- `docs/paper/kd_4agent_paper_facts.md` §2.4 + §0.5 (paper reward + double-objective)
- `scripts/_archive/r20_reward_settled_audit.py` (R20 historical study found PHI_ABS=0 trains anti-paper)
- ADR-0002 (V4 SSOT + paper-faithful framing)

## Resource conflict gate

Zero compute, zero ANDES, zero V4 mutation. Just file inspection + JSON read.
No conflict with R83/R85/R86/R87/R88/R102+.

## Outcome categories

| outcome | next |
|---|---|
| R72_w4 trained on different reward (CONFIRMED) | document as ADR / paper caveat; future round retrains with `paper_strict_pure` |
| Some weights actually match paper after deeper inspection | partial revision; clarify which |
