---
round: R437
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-19'
closed: '2026-08-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R437 plan — a4_md_relaxed 失败块谱诊断 (环 2)

**Opened**: 2026-08-19
**Driver**: R415/CLM-1230 记 a4_md_relaxed 块 (inertia x0.85, damping x1.15)
r_d=0.9712 超 0.95 上限 (+2.2%)，未解释失败机制; 本环对 sealed 记录做
离线频谱诊断，判 bandpass 0.4Hz 通道在该扰动块上是否失配。
**Parent**: CLM-1230 (R415), CLM-1210 (R409), CLM-1195 (R408)

## TL;DR

(完成后填)

## Snapshot at plan-time (oracle as of 2026-08-19)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0111 closed-negative @ R397, by CLM-1130 — Do one-device-at-a-time signed Pref and Qref steps on the two-unit PPVSM1 diagnostic cell produce correctly applied, signed, target-attributed active and reactive power responses without solver or electrical-guard failure, thereby opening only a separately registered droop-slope matching verification?
- Q-0110 closed-positive @ R396, by CLM-1125 — Does the projected-passive dual-droop VSM (PPVSM1) two-unit diagnostic cell pass clean native initialization, a 0.2-second zero-input stationarity gate, and a spectrum guard with no positive-real mode and no neutral degeneracy beyond the network common-angle reference, thereby opening only a separately registered signed P/Q authority gate?
- Q-0109 closed-positive @ R392, by CLM-1105 — Which installed REGF2 feedback path or parameter carries the two reproducible positive-real local modes of the exact R391 four-REGF2 equilibrium, under prospectively frozen one-variable-at-a-time parameter-perturbation EIG arms?

## Methodology

纯离线分析, 无新 ANDES 执行, 无训练, 无 bank 访问。输入 = sealed
`results/research_loop/r415_energy_port_extra_banks/a4_md_relaxed/records.json`
(30 records x 50 steps) + 对照块 a4_md_stiff (通过块) + a4_conditions_b。

- 对象: 四 VSG 能量端口, bandpass_k3p5 vs local_feasibility_native 臂,
  freq_hz_physical / omega 逐臂逐记录轨迹。
- 分析 seam (`probes/r437_relaxed_spectral.py`, 新建, 只读 sealed 数据):
  1. 差分频率构造: 对每 disturbance 记录, 取四 VSG freq 轨迹,
     z_d = T_d Δf (inter-area + 2 局部差分坐标, ROUTE.md 同构),
     差分能量 = ∫z_d² dt 逐臂。
  2. 频域: 每记录做周期图 (Welch, nperseg 10, fs=5Hz, detrend) →
     差分谱密度; 提取 0.1-2.5Hz 带内峰值频率与 0.4Hz 中心 ±0.1Hz 窗口
     内能量占比 (通道失配指标)。
  3. 对照: 同流程跑 a4_md_stiff 与 a4_conditions_b (通过块) →
     失败块 vs 通过块的谱形态差异表。
  4. 输出 hashed JSON `results/research_loop/r437_relaxed_spectral/` +
     `.sha256`, 登记 MANIFEST (LOCAL-ONLY)。
- 判定树 (预注册):
  - 失败块主导差分模式频率显著偏离 0.4Hz 通道 (窗口外能量占比 > 50% 且
    峰值 >0.55Hz 或 <0.25Hz), 且通过块在窗口内 → SUPPORTED:
    "0.4Hz bandpass 通道在松弛惯性块上失配 (模式移频), r_d 失败是
    通道-模式失配而非控制器失效"。
  - 失败块谱形态与通过块无系统差异 (峰值仍在 0.4Hz 窗口内) → 失配假设
    REFUTED, 记边界: r_d 失败机制未由谱诊断定位。
  - 数据不足 (谱分辨率/记录数限制) → UNDECIDABLE, 记 observable 缺口。
- 语言: feed 英文; plan/verdict 紧凑中文。

## Gate

无通过/失败门 — 诊断轮。产出 = hashed 诊断 JSON + 有界结论 (finding,
trust V 或 T 视谱质量) + feed。不改变任何 frozen 资产, 不重训, 不碰
held-out bank。

## Outcomes (pre-registered)

- SUPPORTED: 失败块差分谱峰值落在 0.4Hz±0.1Hz 窗口外 (>0.55Hz 或 <0.25Hz)
  且窗口外能量占比 >50%, 而 ≥1 个通过块峰值在窗口内 → 通道-模式失配
  成立, claim: "a4_md_relaxed 失败是 0.4Hz 通道与扰动块主导模式失配"。
- REFUTED: 失败块与通过块谱形态无系统差异 (峰值均在窗口内或均在外) →
  claim: "谱诊断未定位 r_d 失败机制, 失配假设不成立"。
- UNDECIDABLE: 记录/谱分辨率不足 (如 Welch 峰值无法稳定辨识, 或
  失败块与通过块窗口内占比都 >50% 且峰值接近) → 只记 observable 缺口,
  不开新实验。
- 无论哪支: r_d/r_cross 数值不重算, 引用 R415 sealed 值 (0.9712/0.9833)。

## 资产保护契约

## 资产保护契约

- 只读: R415 records.json (sealed, 不写), R408/R409/R413/R415 所有
  formal JSON, src/ 全部, scripts/ 全部。
- 新建: `probes/r437_relaxed_spectral.py` + 本轮 results 目录 +
  `results/MANIFEST.md` 一行登记。
- 不改: 无任何 src/scripts 修改; 无 ANDES 执行 (无需 WSL, 无需
  Formal launch contract — 本轮无 andes 进程)。

## Cross-references

- CLM-1230 (R415, 失败块源头), CLM-1210 (R409, 通过 heldout),
  CLM-1195/CLM-1200 (R408, 0.4Hz 通道设计), R417 (K=4.0 near-miss)
