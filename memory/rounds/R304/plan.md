---
round: R304
state: completed
opened: '2026-08-03'
closed: '2026-08-03'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R304 plan — VSG 向量动作下的拓扑信息前门

**Driver**: Q-0061；R303 已把异质投影耦合用经典方法关闭，训练若要继续，必须先证明网络配置在真正四维零和 VSG 惯量动作里有独立信息价值。

## TL;DR

本轮不跑时域性能、不训练。先新鲜验证 `nominal/Line_0/Line_9`，跑 `3x7` EIG 静态信息价值门；并用 TDD 增加 `vector_inertia` EVAL，要求请求、命令、ANDES 读回和拓扑 provenance。两门全过也只允许下一轮 12-case 经典信息比较。

## 冻结科学对象

- 物理系统：当前 V4 四 VSG + 已验证慢储能层；会议稿和旧结果只读。
- 配置：`nominal`、经 public `Line.set` 开断 `Line_0`、开断 `Line_9`。`Line_2` 因 CLM-0665 的正实部对预先排除。
- 拓扑语义：同一 Kundur 多重线路系统中的单回线路状态/导纳变化；简单图不变，不叫拓扑泛化。
- 动作：四台 VSG 的惯量 `M`，总和固定 `1400`，公共点 `350`；严格使用 R292 三条路径边 `(0,1),(1,2),(2,3)` 的单边基，边流上限 `0.125`、`dm_max=600`。
- 显式动作顺序：`q0,e01_pos,e01_neg,e12_pos,e12_neg,e23_pos,e23_neg`，禁止依赖 JSON key 排序。
- 动作值：`q0=[350,350,350,350]`；`e01_pos=[275,425,350,350]`；`e01_neg=[425,275,350,350]`；`e12_pos=[350,275,425,350]`；`e12_neg=[350,425,275,350]`；`e23_pos=[350,350,275,425]`；`e23_neg=[350,350,425,275]`。

## Methodology

Stage A 从 R292 incidence/action limit 生成七个动作，不复用 R289 超出该边流盒的 Hadamard 动作。每个 setup 完成的独立系统只经 public setter 改线路状态，随后重新运行 PFlow、TDS 初始化和 EIG；纯 probe 统一识别目标模态、执行守卫、算 per-configuration oracle 与 topology-blind robust-fixed。Stage B 只扩展执行审计和向后兼容 telemetry，不产生或解释性能端点。

## Stage A — 新鲜 3x7 EIG 门

- 每个 cell 新建 plant；setup 后线路状态只经 `evaluation/topology_status.py::apply_line_outage` 设置，再新鲜运行 PFlow、TDS 初始化和 EIG。禁止直接改 `.u.v`。
- 每个配置先过 q0：PFlow converged、`TDS.test_ok=True`、`exit_code=0`、DAE 残差低于 TDS tolerance、finite spectrum、实部 `>1e-7` 数为零。
- 21/21 cell 还必须通过 G4、VSG 数、bus 数、opened-line、总惯量和动作值守卫。
- 模态识别：`0.2--1.5 Hz` 内最大两区有功参与差；同配置相对 q0 要求 cosine `>=0.9`、频率差 `<0.05 Hz`；跨配置 q0 要求 cosine `>=0.8`、频率差 `<0.1 Hz`。
- 每配置 oracle：阻尼比最大动作；平局按显式动作顺序。拓扑盲 robust-fixed：最大化三配置最差 `zeta(action)/zeta(q0)`；平局同顺序。
- headroom：`100*(zeta_oracle-zeta_robust)/abs(zeta_robust)`。物质量门要求 oracle 至少选两种动作、最大 headroom `>=5%`、三配置均值 `>=2%`。
- 旧 R289/R290 只选候选与 API 规则，不复用 endpoint，不从旧 INVALID 矩阵抽数字。

## Stage B — vector-inertia EVAL 就绪门

- 公共 seam：`evaluate(..., execution_profile="vector_inertia")`；旧 scalar 与 `vector_power` 行为逐字节/回归不变。
- 新 trace 契约：record-level topology id、opened line、状态/provenance；step-level raw request、约束后 edge/node residual、commanded VSG `M/D`、从 `GENCLS.M/D.v` 独立读回的 actual 值。
- 审计：shape/finite、edge/node magnitude 与 slew、命令零和、physical residual 零和、command/readback 一致、`D` 不动、活动窗口后归零、拓扑与 sidecar 完整。
- EVAL 只判执行与输入完整性，始终保留 `EXTERNAL_AUTHORITY_REQUIRED`；禁止用 synthetic fixture 产生性能结论。
- 正例：完整 `distributed_edge` 与 `central_vector` 向量惯量 fixture。负例至少逐一破坏 sidecar、topology provenance、actual readback、zero-sum、slew/window 和 D-inactivity。

## 比较可识别性与结论上限

- Stage A 三配置共享 plant family、动作坐标、总惯量、模态规则、数值守卫和计算预算；唯一变化是线路状态。
- oracle 是 outcome-seeing 静态上界，只识别 configuration-conditioned action headroom，不是可部署控制器。
- 本轮不比较 centralized/agent 网络，不识别架构价值、局部信息充分性或动态控制性能。
- `Decoupling-Oriented` 只允许指零和公共/差分控制接口；R304 不支持当前会议稿的 MARL 结果，也不回填稿件。

## 预注册判定

1. 任一 q0 或 cell 有效性/分支守卫失败 -> `INVALID-TOPOLOGY-GATE`；停止，不解释 headroom。
2. 21/21 有效但 oracle 动作数或 `5%/2%` 门失败 -> `NO-STATIC-TOPOLOGY-VALUE`；停止后续 12-case 与训练。
3. 静态价值门过、EVAL 就绪门失败 -> `STATIC-TOPOLOGY-VALUE-EVAL-NOT-READY`；只修执行审计，不跑时域。
4. 两门都过 -> `STATIC-TOPOLOGY-VALUE-EVAL-READY`；只授权下一轮冻结 12-case 的 topology-blind / configuration-conditioned local classical / centralized constrained reference，不授权 neural smoke。

所有分支：`training_authorized=false`、`training_executed=false`。

## TDD 与执行

- 确认 seam：safe topology qualification、vector-inertia EVAL、R304 fail-closed classifier。
- 每 slice 红后绿：先 EVAL profile/fixture，再 readback telemetry，再 seal/analyser，再 WSL adapter。
- 工程验证：focused pytest、旧 EVAL tests、R292 vector tests、R290 topology tests、Ruff、compileall。
- ANDES 只在预检通过后经 `scripts/andes_scratch.py`；最多三个 WSL worker，seal-first、create-only、每 JSON sidecar。
- Ask Matt 收尾做 Standards/Spec 双轴并行复核；审查通过后才写 canonical summary。

## 资产保护契约

- 不改 `paper/icems2026/`、旧 claims/verdict/seals/results、V4 plant、`base_env.py`、`andes_vsg_env_v4.py`、训练器或 checkpoint。
- 允许写：R304 question/plan/seal/verdict、EVAL 与 R292 wrapper 的向后兼容 telemetry seam、新 R304 probe/adapter/tests、create-only results/feed/claim/manifest/programme 状态。
- 当前会议论文继续以 scalar shared factorization 为上限；R304 永久 stay-out。

## Cross-references

- Q-0061；CLM-0665、CLM-0720、CLM-0725。
- `src/andes_rl_kundur/evaluation/topology_status.py`。
- `src/andes_rl_kundur/control/vector_inertia_residual.py`。
- `src/andes_rl_kundur/evaluation/eval_v2.py`。
