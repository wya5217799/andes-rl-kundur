---
round: R303
state: completed
opened: '2026-08-03'
closed: '2026-08-03'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R303 plan — 异质裕度下的差分残差投影门

**Driver**: Q-0060；R300 的 2Kv 在投影前严格零和，但设备独立功率、爬坡、SOC 投影可能把差分动作泄漏到公共有功。

## TL;DR

先做代数和单元探针，不跑 ANDES、不训练。比较独立投影、邻居端点 headroom-aware 边流和集中式零和盒约束 oracle。若经典邻居算法已修好坐标缝，继续 BLOCK 训练；若仍有局部信息缺口，也只允许下一轮冻结更强经典比较与单次 neural smoke，不在本轮开训。

## 冻结对象

- 物理动作：四个 ESD1 系统基准有功，沿用 R272 功率、爬坡、SOC、能量、电流能力契约；M/D 固定。
- 通信图：规则环边 `(0,1),(1,2),(2,3),(0,3)`；两相无冲突调度 `[(0,1),(2,3)] -> [(1,2),(0,3)]`。
- 差分请求：固定 `2Kv=0.4884814`、degree=2，由预设 filtered-RoCoF 向量生成反对称边流；不读性能结果调参。
- 公共请求：每设备 `+0.04` 或 `-0.04` system pu。
- RoCoF 模板：正/负 inter-area、单节点 outlier、alternating；幅值只取预设 `{0.04,0.08,0.12}` Hz/s 组合。
- headroom 模板：homogeneous-mid、SOC split、ramp split、mixed SOC+ramp；固定 `dt=0.2 s`、电压 `1.0 pu`。

## 比较识别契约

三个 arm 共享目标边流、四维动作坐标、设备约束、时刻和 case：

1. `independent_projection`：各设备直接投影公共+差分请求；识别未协调投影的坐标泄漏。
2. `local_edge_allocator`：每条边仅看两个端点剩余上下界，按冻结两相邻居调度裁剪反对称边流；识别此具体分布式经典修复。
3. `central_zero_sum_oracle`：联合盒约束+零和超平面欧氏投影；只作最优参考，不作可部署控制器。

允许结论只到投影协调机制和这一个规则环实现。禁止纯架构、MARL、拓扑泛化、硬解耦、稳定性、安全或部署结论。

## Methodology

先由真实 BESS 投影契约求每个设备在当前 previous-power、SOC、电压和步长下的可行区间。再把同一公共请求和固定 2Kv 边流送入三个冻结 arm，只读取动作几何、约束和坐标指标；不读取频率性能端点。最后由单一 probe 按下列 Outcomes 判定。

## 预注册指标与判定

- `common_leakage = sum(command_with_residual - projected_common)`。
- `target_error = ||executed_differential - requested_differential||_2`。
- `retained_fraction = ||executed_differential||_2 / ||requested_differential||_2`。
- 有效性：所有请求零和误差、动作上下界、local/oracle 公共泄漏均 `<=1e-12`；oracle KKT/盒约束通过。
- 独立投影发生机制泄漏：任一异质 case `abs(common_leakage)>1e-12`。
- 物质量门：至少两个异质 case 同时满足 `abs(leakage)>=0.01 system pu` 且相对半 L1 差分请求 `>=10%`。
- 经典修复充分：local 全部有效；在物质量 case 中 median retained fraction `>=0.5`，且 local target error 不超过 oracle error 的 `1.25x + 1e-12`。

判定树：

- guard 失败 -> `INVALID-PROJECTION-PROBE`，停。
- 无机制泄漏 -> `PROJECTION-SEAM-PRESERVED`，训练 BLOCK。
- 有数值机制泄漏但不足两个 case 通过物质量门 -> `PROJECTION-LEAKAGE-IMMATERIAL`，训练 BLOCK。
- 有物质泄漏且经典修复充分 -> `COUPLING-CLASSICALLY-CLOSED`，训练 BLOCK。
- 有物质泄漏、local 保持可行/零和但明显落后 oracle -> `LOCAL-CLASSICAL-GAP`；只开放下一轮更强分布式优化与冻结 neural smoke 的比较设计，本轮不训练。
- local 不能保持可行/零和 -> `COORDINATE-REPAIR-FAILED`，先修控制算法，训练 BLOCK。

### Outcomes

- `INVALID-PROJECTION-PROBE`：任一零和、盒约束或 oracle KKT guard 失败；不解释方向。
- `PROJECTION-SEAM-PRESERVED`：全部异质 case 泄漏 `<=1e-12`；否定 Q-0060 机制并继续 BLOCK 训练。
- `PROJECTION-LEAKAGE-IMMATERIAL`：存在超过 `1e-12` 的泄漏，但不足两个 case 同时通过 `0.01 pu` 与 `10%` 门；不升级到动态仿真或训练。
- `COUPLING-CLASSICALLY-CLOSED`：至少两个 case 达到 `0.01 pu` 与 `10%` 双物质量门，且 local 满足 `0.5` retention 与 `1.25x` oracle error 门；经典修复充分，训练 BLOCK。
- `LOCAL-CLASSICAL-GAP`：物质泄漏成立，local 零和/可行但未过 retention 或 oracle-gap 门；只开放下一轮比较设计。
- `COORDINATE-REPAIR-FAILED`：物质泄漏成立但 local 零和或可行 guard 失败；先修算法。

## Cross-references

- Q-0060；CLM-0710；CLM-0715；CLM-0720。
- R300 fixed 2Kv formal summary；R302 architecture-aware vector EVAL gate。

## TDD seam 与验证

- 公共 seam：BESS 契约给出当前设备可行有功区间；headroom-aware allocator 从公共基线、边流、区间和冻结边调度返回执行动作与裁剪边流。
- 每次 red-green 一条行为：无约束恒等、单边裁剪仍反对称、两相规则环全局零和/可行、集中 oracle KKT、完整预设矩阵分类。
- `python -m pytest tests/test_headroom_aware_edge_allocation.py tests/test_r303_projection_coupling_probe.py -q`
- `python -m ruff check` 覆盖新增/修改文件；Ask Matt 最后做 Standards+Spec 双轴复核。
- 本轮无兼容 ANDES trace，EVAL-v2 不伪造输入；若代数门触发后续 ANDES，必须用 R302 `vector_power` profile 做完整执行审计并保留 `EXTERNAL_AUTHORITY_REQUIRED`。

## 会议标题门

- `Decoupling-Oriented` 只允许写成约束前后控制器公共/差分坐标分离，不等于非线性电网硬解耦。
- `Multi-Agent Reinforcement Learning` 只有未来四个真实本地 learned agents 通过匹配经典基线和 sealed eval 才可由新证据支持；R303 是经典控制，不支持该词。
- 当前执行器是同址 GFL ESD1，而不是 VSG M/D 或独立 VSG `P_ref`；未解决 actuator/title 对齐前，R303 留在未来工作，禁止回填现有 ICEMS 数字或改稿。

## 资产保护

- R300–R302 seals、records、summaries、feeds、claims 只读。
- 不改 V4 plant、base_env、paper-grade ranker、训练器或任何 manuscript 文件。
- 只写 R303 plan/probe/tests、可复用控制 seam、结果 JSON+sidecar、feed/claim/verdict 和 programme 治理。

## Execution amendment

- 2026-08-03、final artifact 前：Ask Matt Spec review 发现原逻辑把 `local_valid` 同时当实验有效性 guard 和候选 arm 结果，导致预注册 `COORDINATE-REPAIR-FAILED` 不可达。现区分 core validity（请求零和、oracle 盒约束/KKT、有限矩阵）与 local candidate validity；分类、阈值、case 和已观察数值不变。
- Ask Matt Standards review 要求结论 JSON/sidecar create-only；pre-review 快照移入 `tmp/R303/pre_review/`，canonical final 禁止覆盖。
