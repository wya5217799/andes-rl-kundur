---
round: R450
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-20'
closed: '2026-08-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R450 plan — P2 同银行零延迟补点与功率命令断环复响应

**Opened**: 2026-08-20
**Driver**: 咨询包 P2 已有 R440 的一、二步延迟端点，但缺同银行零延迟与
名义复环路，无法把端点边界和纯延迟相位效应相连。
**Parent**: CLM-1350 (R440 delay boundary); CLM-1395 (R447 complex seam);
CLM-1400 (R449 bounded sensitivity); NOTE-0031。

## TL;DR

同银行零延迟补点通过；0 到 1 个采样之间出现预注册端点边界，且名义
MIMO 纯延迟模型在 1/2 步均正确预测恶化方向，归一化曲线误差低于 10%。

## Methodology (冻结契约)

- 非线性补点只新跑 `delay_steps=0`，严格复用 R440 nominal topology、
  seed 42、0.2 s × 50 steps、三臂、8 paired probes + 2 disturbances、
  action map、headroom、守卫和汇总器；R440 已哈希的 delay 1/2 summaries
  只读复用，不重跑。
- **断环定义**：在带通控制器的归一化输出进入 0.072 pu 功率映射前断开；
  注入量是四台设备的功率命令 `u`，回读量是同一控制器读取的四维频率偏差
  `y`。负反馈为 `u=-K(z)y`；控制延迟位于 K 输出后，故乘 `z^-n`。
- 名义离散对象：`P_c(z)=C(zI-A_d)^(-1)B_c`，扰动通道
  `P_d(z)=C(zI-A_d)^(-1)B_d`；环路矩阵
  `L_0(z)=P_c(z)K(z)`，其中
  `K(z)=B_ring F(z) B_ring^T`，F 为冻结二阶带通。
- 精确 MIMO 延迟响应：
  `G_n(z)=[I+z^(-n)L_0(z)]^(-1)P_d(z)`；本地参照 `G_L` 不加延迟；
  0.3–0.5 Hz 差分能量比给线性预测 `r_d^lin(n)`。
- 比较形状而非绝对能量：
  `q_n^lin=r_d^lin(n)/r_d^lin(0)`，
  `q_n^nl=r_d^nl(n)/r_d^nl(0)`，n∈{1,2}。

## Theory intake

```
observable: same-bank nonlinear delay curve n=0,1,2
  definition: bandpass/local mean differential-frequency energy ratio on the frozen R440 bank
  source: results/research_loop/r450_p2_delay_loop/formal_analysis.json#/nonlinear
  predicts: n=0 passes and n=1 fails => endpoint boundary lies between zero and one sample
observable: measured command-break loop L0 and pure-delay prediction
  definition: L0=PcK at the pre-power-map command break; compare normalized q_n curves
  source: results/research_loop/r450_p2_delay_loop/formal_analysis.json#/linear_loop
  predicts: same direction and <=10% relative curve error at n=1,2 supports bounded phase-delay consistency; wrong direction or >10% refutes; singular return difference is invalid
```

## Gate (判定树)

- 全部零延迟记录完成且守卫/汇总有效；R440 delay 1/2 sidecar 匹配；
  线性 `r_d^lin(0)` 与新非线性 `r_d^nl(0)` 相对差 <=10%；
  频带内 `min σ(I+z^-nL_0)>1e-8` → seam 有效。
- 有效后，n=1,2 的 `q` 方向一致且相对误差均 <=10%
  → `PHASE-DELAY-CONSISTENT`；否则 `PHASE-DELAY-REFUTED`。
- 任一来源、sidecar、记录、分母、有限性或 return-difference 门失败
  → `CANARY-INVALID`，不重试。
- 端点边界独立报告：若 n=0 的 `r_d<=0.95` 且 n=1 的 `r_d>0.95`，
  则只称 `BETWEEN-0-AND-1-SAMPLE-ENDPOINT-BOUNDARY`；不称稳定裕度。

## Outcomes (pre-registered)

- `PHASE-DELAY-CONSISTENT`: 两个延迟档均满足方向与 10% 曲线误差门。
- `PHASE-DELAY-REFUTED`: seam 有效但任一档方向反或误差超 10%。
- `CANARY-INVALID`: Gate 的完整性条件失败。

## Formal launch contract

- `formal_entry`: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r450_p2_delay_loop.py analyse` (WSL)。
- `rehearsal_command`: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r450_p2_delay_loop.py rehearse` (WSL)。
- `rehearsal_scope`: 一个零延迟 bandpass probe record + 名义复环路；不写 formal。
- `rehearsal_checks`: parent sidecars；单记录 50 steps、无 TDS failure；
  n=0 线性比有限；输出不存在；断环维度 4×4。
- `capacity_evidence`: 新执行仅 R440 同银行零延迟 30 条串行记录，约 6 min；
  owner 的 <=20 min 单进程 seam 规则适用，无 shard/训练。
- `host_process_budget`: 1；`other_reserved_processes`: 0；
  `wsl_python_processes`: 1；`native_threads_per_process`: 1。

## 资产保护契约

- 只读：R440 delay 1/2 与 sidecars、R447/R449、`src/`、既有 runners。
- 新建：`scripts/run_r450_p2_delay_loop.py`、定向测试、
  `results/research_loop/r450_p2_delay_loop/`；formal JSON create-only + sidecar。
- seal 后失败 → aborted；不原轮补丁重跑。

## Cross-references

- CLM-1350, CLM-1395, CLM-1400, NOTE-0031;
  advisory `problems/P2_delay_boundary.md`;
  `working/route_owner_decision_advisory_unresolved_2026-08-21.md`。
