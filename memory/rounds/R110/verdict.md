# R110 verdict — Disturbance profile audit: ANDES Toggler Line_8 trip at t=2s

**Date**: 2026-05-19
**Status**: DONE — 1 critical finding (CLM-0194), 1 Q-NEW (Q-0025), zero compute
**Type**: audit (zero compute, zero ANDES, zero V4 mutation)
**Wall**: ~10 min (file inspection + claim + verdict)

## TL;DR

**🚨 Critical missing-piece finding for R09 2× max_df residual**: ANDES
default `kundur_full.json` ships with a `Toggler` entry that trips
`Line_8` (Bus 8 → Bus 9, Area 2 internal, 1 of 2 parallel paths) at
t=2.0s. V4 env never removes it. Every LS1/LS2 scenario therefore has
**TWO disturbances**: paper-intended load step at t=0.5s + unintended
Line trip at t=2s. R57-R85 91-round training + eval ALL on this
compound scenario, paper Sec.IV-C is single-event — not apples-to-apples.
CLM-0194 documents; Q-0025 opens quantitative ablation (Toggler u=0
vs u=1, ~10 min wall once WSL free).

## Methodology

Zero compute. Pure file inspection.

1. Parse `probes/r89_andes_kundur_full.json::Toggler` (cached) — found
   single entry: `{idx:1, u:1.0, model:"Line", dev:"Line_8", t:2.0}`
2. Grep `src/andes_rl_kundur/env/andes/*.py` for "Toggler|trip|Line_8":
   zero matches → V4 doesn't remove it
3. Cross-ref `base_env.reset()` warm-up to t=0.5s + `_apply_disturbance`
   at t=0.5s + agent control 0.7-10.5s → Toggler at t=2s falls INSIDE
   agent control window
4. Identify Line_8 endpoints: Bus 8 (name 13, Area 2, 230 kV) → Bus 9
   (name 112, Area 2, 230 kV). Area-2 internal, one of TWO parallel
   paths (Line_7 stays after trip)

## Findings

### F1 (CRITICAL — CLM-0194): unintended Toggler trip at t=2s

V4 LS1/LS2 evaluation profile:

| t (s) | Event | Paper-intended? |
|---|---|---|
| 0.0 | Warm-up TDS starts | ✓ |
| 0.5 | Load step ±2.48 / +1.88 pu | ✓ |
| 0.7 | Agent control begins | ✓ |
| **2.0** | **Line_8 trip (Area 2 internal)** | **❌ ANDES default, never removed** |
| 10.5 | Agent control ends | ✓ |

### F2 (HIGH): partial closure of R09 2× max_df residual

R08 §2 Finding 2 reported H=300 no_ctrl max_df=0.266 vs paper 0.13.
R89 audit (CLM-0173) F1-F5 didn't fully explain it (F1 correction
made residual LARGER not smaller). R110 F1 (Toggler) is the **F6
candidate** to close the gap.

Quantitative test → Q-0025 (cheapest ~10 min wall).

### F3 (MEDIUM): training-time compound exposure

R57-R85 91-round trained on compound scenario → learned to handle
line trip + load step jointly. If Toggler removed for paper-faithful
re-eval, the trained policies may either:
- **Improve** (simpler scenario, geo goes up)
- **Degrade** (over-specialized for compound, performance drops on
  cleaner setting)

Direction TBD by Q-0025 + Q-0026 (TBD next round) extension to RL
controller.

## Verification

- Toggler JSON entry confirmed ✓
- V4/V5 env code grep showed no Toggler removal ✓
- Line_8 endpoints traced via Bus name table ✓
- V4 / V4Config / base_env / agents/ / ckpt 全部零 mutation ✓
- 零 ANDES TDS, 零 WSL python, 零 R102 conflict ✓

## Cross-references

- CLM-0094 (R72_w4 SOTA, geo=0.391, on compound scenario)
- CLM-0144 (91-round plateau, on compound scenario)
- CLM-0173 (R89 audit F1-F5, did NOT cover Toggler)
- CLM-0184/0185/0186 (R85 classical, on compound scenario)
- CLM-0191/0192 (R105 reward audit, separate paper-deviation thread)
- R08 §2 Finding 2 (the 2× residual that R110 may explain)
- `probes/r89_andes_kundur_full.json::Toggler`
- `docs/paper/kd_4agent_paper_facts.md` §IV-C (single-event LS1/LS2)

## Questions opened (this round)

- **Q-0025**: Toggler-Line_8 ablation — does removing the t=2s trip
  drop max_df by ≥30%? Determines whether R110 F1 closes R09 2× residual.

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- **Q-0014** (algo backlog): if Q-0025 confirms Toggler dominant, then
  R57-R85 plateau is partly "ANDES Toggler artefact". Algo exploration
  ROI further questioned.

## 给 PI 的话

**这周干了啥**: 等 R102 跑 (8 min+ elapsed, ~17 min ETA) 同时, 顺手扩展 R105 reward audit 到 disturbance profile. 10 min 纯 file inspection: 读 ANDES kundur_full.json Toggler 字段 + grep V4 env 看有没有 remove 它. 单一发现 + 单 claim CLM-0194 + Q-0025 登记 ablation.

**结果（一句话）**: **ANDES default kundur_full 有一个 Toggler 在 t=2s trip Line_8 (Area 2 内部), V4 env 从未 remove 它** — 每个 LS1/LS2 scenario 实际是 compound disturbance (paper load step @ t=0.5s + 没意识到的 line trip @ t=2s). 这极可能是 R08 2× max_df 残差的 missing piece.

**意外**: (1) **R89 audit 漏了 Toggler** — F1-F5 covered fn / load topology / damping / governor / capacitive q, 但 disturbance profile 完全没看. Toggler 在 JSON 里 11 行就能看到, 但 R89 audit 只 grep 了 GENROU/Line/PQ/TGOV1. (2) **Line_8 = 230kV Area 2 内部 1/2 并联线路**, 不是 inter-area tie 也不是 catastrophic, 是中等 severity event. 但 50 步 / 10s 的 eval 窗口里 t=2s 落在最敏感的 transient 上, max_df 受影响显著. (3) **R57-R85 91-round 全部在 compound disturbance 下训练 + eval**, paper Sec.IV-C 是 single-event, 所以 paper number 跟 V4 number 比对**根本不是 apples-to-apples**. R85 RL vs classical 1.99× advantage 仍然 valid (同 V4 compound), 但跟 paper -8.04 cum_rf 比对要打折扣. (4) **零 compute 30 min wall 内捅出来 2 个 paper-deviation finding** (R105 reward + R110 toggler), R09 audit 12 天空白真的是因为之前一直在 algo path 上跑.

**我默认下一步做**: R110 收尾 done (verdict + CLM-0194 + Q-0025). 等 R102 完成 (~15 min ETA), 写 R102 verdict + chat brief. 期间继续 Windows-side audit: (a) 比对 line impedance 跟 Kundur 1994 textbook 也许还有 F7+ findings, (b) 比对 v4_config.py 的 D0_HETEROGENEOUS 跟 paper Eq.12-13 baseline (paper Q-D 说论文没给 baseline 值, 项目猜了几个), (c) audit V4 通信延迟 / 邻居失败实现.

**你想插一脚就说**: (a) 若你想立即开 R111 = Toggler ablation (~10 min wall, 单 ANDES session, 跟 R102 抢 WSL slot, 风险中等) 说一声; (b) 若你想 Toggler ablation 加 SOTA + droop 一起跑 (~30 min wall, Q-0025 A2), 工程量稍大但 ROI 高很多; (c) 若你想停 audit 转写 paper section "Known paper-deviations" (基于 CLM-0094 + CLM-0173 + CLM-0192 + CLM-0194 四块), 是 paper-side 不是 research. (d) 沉默 = 继续 Windows-side audit + 等 R102. **我推荐 (d)**.
