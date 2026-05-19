---
round: R103
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R103 plan — Reward shape ablation: R72_w4 hyper × paper_strict_pure × 75 ep s54

**Status**: ACTIVE
**Opened**: 2026-05-19
**Driver**: [[CLM-0168]] PRIORITY 2 after CLM-0163 retraction. With critic
([[CLM-0160]]) and obs-for-action ([[CLM-0168]]) ruled out as plateau
mechanisms, reward shape becomes the leading candidate. R72_w4 SOTA was
trained on `V4Config.paper_faithful()` (PHI_ABS=50 + PHI_H/D=0.0056
rescale, R56 / R57 era). `paper_strict_pure` is the paper Eq.14 nominal
(PHI_ABS=0, PHI_H=PHI_D=1.0) — never combined with the R72_w4 LSTM
hyper basin in any prior round.

**Parent**: CLM-0144 (91-round algo plateau), CLM-0160 (critic OK),
CLM-0168 (obs OK, value-horizon retracted).

## TL;DR

Train td3_lstm at R72_w4 hyper (warmup=5, h=64, tau=0.001, normalized
actions, seed=54, 75 ep) but with `--reward-config paper_strict_pure`.
Final-eval on LS1+LS2. If geo ≥ 0.40 → reward shape matters; PHI_ABS=50
was contributing to the plateau. If geo ≤ 0.40 (essentially baseline
0.391) → reward shape is NOT the plateau lever either.

Either outcome is meaningful:
- positive → R104 explores reward redesign space
- negative → reward shape joins critic + obs in the "not the mechanism"
  pile; remaining candidates narrow to env stochasticity / policy class /
  long-horizon

Wall: ~30 min training, 1 WSL slot.

## Launch

```bash
wsl -e bash -c "source /home/wya/andes_venv/bin/activate && \
  cd /mnt/c/Users/27443/Desktop/andes-rl-kundur && \
  python3 scripts/train.py \
    --algo td3_lstm \
    --reward-config paper_strict_pure \
    --episodes 75 \
    --seed 54 \
    --hidden-size 64 \
    --tau 0.001 \
    --lstm-lr-warmup-eps 5 \
    --normalize-actions \
    --save-dir results/r103_w1_paper_strict_pure_s54 \
    --final-eval \
    2>&1 | tee results/r103_w1_stdout.log"
```

Difference from R72_w4 baseline: ONLY `--reward-config paper_strict_pure`.
All other hyper identical. Single-axis ablation.

## Success criteria

| Outcome (final_eval geo) | Verdict |
|---|---|
| ≥ 0.50 | reward shape was a strong lever; CLM-0168 plateau-mechanism candidate confirmed |
| ∈ [0.42, 0.50] | reward shape helps, but doesn't fully break plateau |
| ∈ [0.34, 0.42] | reward shape is a wash (within noise band of 0.391 baseline) |
| < 0.34 | strict reward HURTS performance; PHI_ABS=50 was actively useful |
| TDS divergence / training crash | strict reward + R72_w4 hyper is unstable; new infra Q |

## 资产保护契约

不动 V4 / V4Config / base_env / paper_grade_axes / agents/ / R57+ ckpt.
新建: `results/r103_w1_paper_strict_pure_s54/` ckpt dir,
`memory/rounds/R103/{plan.md, verdict.md}`, 1 CLM (≥ 0173).

V4Config.paper_strict_pure() already exists (R58 ADR-0002 infrastructure).
This is a *use*, not a *creation*.

## Cross-references

- [[CLM-0168]] (R96 retraction, sets up this PRIORITY 2 candidate)
- [[CLM-0144]] (91-round plateau evidence)
- [[CLM-0073]] (R58 sanity: paper_strict_pure × SAC/TD3 produced 6-axis ~0)
- R58 verdict (paper_strict_pure infrastructure; no TD3+LSTM trained
  at this config yet — this is the first time)
