# V5 env: REGCA1 风机 plant 升级，框定为 paper-deviation

**Date:** 2026-05-19
**Status:** accepted

## Context

V4 env 当前 plant 含两个"假风机"近似：
- G4 @ Bus 11 = GENROU + `ZERO_G4_INERTIA=True`（H=0 同步机退化为风机近似）
- W2 @ Bus 8 = GENCLS M=0.1（低惯量同步机代理 100MW 风电场）

R08 verdict (CLM 系列) 实测在 H=300 物理极限下 max_df 仍 2× paper Fig.6 (0.266 vs 0.13 Hz)。
handoff `2026-05-18` 提议升级 G4/W2 到 ANDES REGCA1 真风机模型，理由是 "更 paper-faithful"。

Grill (R80 准备阶段，11 轮 question 验证) cross-reference paper 全文得到两个决定性事实：

1. **paper Sec.IV-A 风机模型沉默** —— 全部信息仅 "wind farm with same capacity" + "100 MW wind farm at bus 8"。paper 未指定 Type 3/4 / GFL/GFM / WECC trio / inertia emulation。
2. **paper Sec.II line 259-263 显式声明** —— "this paper mainly studies the relatively slow dynamics of the electromechanical transient. Therefore, the dynamics of the inner loop can be neglected."

→ REGCA1（带 PE current 内环、限幅、LVRT）实际**比 GENCLS M=0.1 离 paper Sec.II 声明更远**。GENCLS 是纯 swing 方程，符合 "neglect inner loop"；REGCA1 多了 paper 显式不要的层次。

"REGCA1 = paper-faithful" 立论站不住。

## Decision

新建 V5 env (`andes_vsg_env_v5.py` + `v5_config.py`)，G4 + W2 同时换 REGCA1 (+ REECA1 if needed by ANDES)，**与 V4 env 并存**。

Framing 显式调整：**V5 是 ANDES 侧 plant 颗粒度工程升级，paper-deviation**。
不再声称 "更 paper-faithful"。Contribution narrative 在 C3 cross-eval / C2 ablation / C1 main result / C4 negative finding 之间，按阶梯实验结果定。

V4 / V4Config / base_env / paper_grade_axes.py / R57+ SOTA ckpt 全部不动。新 ckpt 走 `r80+_*` namespace。

## Considered Options

- **(a) "Paper-faithful" framing** — 拒绝：与 paper Sec.II inner-loop-neglect 直接矛盾。
- **(b) "ANDES 工程升级" framing** — 选中：诚实，可解释。
- **(c) 放弃 V5, 改追 R09 副线 (line/load/SBASE audit)** — 备选，若 V5 阶梯 Phase B failed 可回退此路径。

## Consequences

- 未来 reviewer 问 "REGCA1 为何符合 paper" 时，答案是 **"不符合 paper Sec.II 声明，是工程取向 plant 升级"**，不假装 paper-faithful。
- V5 ckpt 不能作为 "paper-equivalent SOTA" 写入 main result，除非阶梯走到 Phase D (C1) 且数字突破。
- V4 仍是 paper path canonical（CONTEXT.md `paper path` 定义不变）。
- Asset 4 `paper_grade_axes.py` 评分函数不变 — V5 数字进同一个 ranker。
