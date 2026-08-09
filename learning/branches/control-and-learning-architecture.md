# `Control and Learning Architecture | 控制与学习架构`

## `Active-Power Control Channel | 有功功率控制通道`

- **Type**: `Foundation`
- **Requires**: `Power Imbalance`
- **Used in**: `dynamic-mechanism`, `control-architecture`, `simulation-implementation`
- **Project role**: 说明控制器如何通过改变有功功率影响频率，同时区分请求、受限命令与实际执行功率。
- **Anchors**:
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#executable-gencls-and-esd1-equations`
  - `explains` → `paper/icems2026/working/chapter_blueprint.md#ii-decoupled-control-problem`

## `Fast–Slow Control Decomposition | 快慢控制分解`

- **Type**: `Foundation`
- **Requires**: `Active-Power Control Channel`, `Control-Objective Separation`
- **Used in**: `control-architecture`, `experimental-validation`
- **Project role**: 把快速暂态支撑与较慢的持续频率恢复分开理解，是会议论文控制结构的主入口。
- **Anchors**:
  - `explains` → `paper/icems2026/working/chapter_blueprint.md#ii-decoupled-control-problem`

## `Zero-Sum Action Constraint | 零和动作约束`

- **Type**: `Foundation`
- **Requires**: `Common–Differential Decomposition`, `Active-Power Control Channel`
- **Used in**: `control-architecture`, `simulation-implementation`
- **Project role**: 保证差分动作只重新分配设备间功率而不直接改变全体设备的净有功支撑。
- **Anchors**:
  - `explains` → `paper/icems2026/working/chapter_blueprint.md#iii-hard-zero-sum-learning-architectures`
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#common-differential-and-graph-coordinates`

## `Scalar Action Projection | 标量动作投影`

- **Type**: `Foundation`
- **Requires**: `Zero-Sum Action Constraint`
- **Used in**: `control-architecture`, `simulation-implementation`
- **Project role**: 解释多个局部输出如何被压缩成一个共同执行方向，是理解会议论文动作空间的关键。
- **Anchors**:
  - `explains` → `paper/icems2026/working/chapter_blueprint.md#iii-hard-zero-sum-learning-architectures`

## `Graph-Incidence Action Basis | 图关联矩阵动作基`

- **Type**: `Foundation`
- **Requires**: `Zero-Sum Action Constraint`, `Synchronizing Coupling`
- **Used in**: `control-architecture`, `simulation-implementation`
- **Project role**: 用边流自动生成总和为零的节点动作，并保留多个独立差分控制自由度。
- **Anchors**:
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#common-differential-and-graph-coordinates`

## `Runtime Information Pattern | 运行时信息结构`

- **Type**: `Foundation`
- **Requires**: `None`
- **Used in**: `control-architecture`, `experimental-validation`
- **Project role**: 区分控制器执行时究竟能看到本地、邻居还是全局信息，防止只凭算法名称判断是否分布式。
- **Anchors**:
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#comparator-and-estimand-contract`
  - `explains` → `paper/icems2026/working/chapter_blueprint.md#iii-hard-zero-sum-learning-architectures`

## `Parameter Sharing | 参数共享`

- **Type**: `Foundation`
- **Requires**: `Runtime Information Pattern`
- **Used in**: `control-architecture`, `experimental-validation`
- **Project role**: 解释多个局部决策器共用同一组网络参数的含义，并把它与运行时分散执行区分开。
- **Anchors**:
  - `explains` → `paper/icems2026/working/chapter_blueprint.md#iii-hard-zero-sum-learning-architectures`

## `Centralized Action Aggregation | 集中式动作聚合`

- **Type**: `Foundation`
- **Requires**: `Scalar Action Projection`, `Runtime Information Pattern`
- **Used in**: `control-architecture`, `experimental-validation`
- **Project role**: 说明多个局部建议若必须在中心合成为一个动作，部署结构仍含有集中执行环节。
- **Anchors**:
  - `explains` → `paper/icems2026/working/chapter_blueprint.md#iii-hard-zero-sum-learning-architectures`

## `Neighbour Message Passing | 邻居消息传递`

- **Type**: `Foundation`
- **Requires**: `Runtime Information Pattern`
- **Used in**: `control-architecture`, `simulation-implementation`
- **Project role**: 定义相邻控制器交换哪些信息以及何时可用，是模型优先路线分布式执行的通信基础。
- **Anchors**:
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#deterministic-and-neural-controller`

## `Independent Vector Action | 独立向量动作`

- **Type**: `Foundation`
- **Requires**: `Graph-Incidence Action Basis`, `Runtime Information Pattern`
- **Used in**: `control-architecture`, `simulation-implementation`
- **Project role**: 让不同边或设备保留各自的动作自由度，而不是在执行前被压缩成单一标量。
- **Anchors**:
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#research-objective`
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#comparator-and-estimand-contract`

## `Decentralized Execution | 分散执行`

- **Type**: `Foundation`
- **Requires**: `Independent Vector Action`, `Neighbour Message Passing`
- **Used in**: `control-architecture`, `experimental-validation`
- **Project role**: 要求每个控制单元仅凭声明的信息独立产生动作，是判断多智能体部署含义的核心标准。
- **Anchors**:
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#research-objective`

## `Deterministic Control Backbone | 确定性控制骨架`

- **Type**: `Foundation`
- **Requires**: `Reduced-Order Predictor`, `Runtime Information Pattern`
- **Used in**: `control-architecture`, `experimental-validation`
- **Project role**: 先用可分析的控制器承担基本稳定、约束与性能责任，再判断学习部分是否还有必要。
- **Anchors**:
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#deterministic-and-neural-controller`

## `Residual Control | 残差控制`

- **Type**: `Foundation`
- **Requires**: `Deterministic Control Backbone`, `Control-Objective Separation`
- **Used in**: `control-architecture`, `experimental-validation`
- **Project role**: 让学习策略只修正确定性控制器尚未解决的部分，而不是从头接管全部控制任务。
- **Anchors**:
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#deterministic-and-neural-controller`

## `Action Headroom | 动作余量`

- **Type**: `Foundation`
- **Requires**: `Active-Power Control Channel`, `Zero-Sum Action Constraint`
- **Used in**: `control-architecture`, `experimental-validation`
- **Project role**: 表示满足功率、爬坡、电流与能量约束后仍可留给附加控制动作的可用空间。
- **Anchors**:
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#deterministic-and-neural-controller`
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#training-and-eval-gates`

## `Governed Residual Control | 受约束残差控制`

- **Type**: `Foundation`
- **Requires**: `Residual Control`, `Action Headroom`, `Decentralized Execution`
- **Used in**: `control-architecture`, `experimental-validation`
- **Project role**: 把学习残差限制在确定性控制器预留的安全权能内，是模型优先路线的目标控制形态。
- **Anchors**:
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#deterministic-and-neural-controller`

## `Matched Comparator | 匹配比较器`

- **Type**: `Foundation`
- **Requires**: `Control-Objective Separation`, `Runtime Information Pattern`
- **Used in**: `experimental-validation`, `evidence-and-paper-claim`
- **Project role**: 要求比较对象使用一致的动作、信息、预算、场景与评价指标，使性能差异具有可解释性。
- **Anchors**:
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#comparator-and-estimand-contract`
  - `explains` → `paper/icems2026/working/chapter_blueprint.md#iii-hard-zero-sum-learning-architectures`

## `Causal Identifiability | 因果可辨识性`

- **Type**: `Foundation`
- **Requires**: `Matched Comparator`, `Runtime Information Pattern`
- **Used in**: `experimental-validation`, `evidence-and-paper-claim`
- **Project role**: 判断观察到的差异能否归因于目标架构因素，而不是信息、动作空间或控制预算等混杂因素。
- **Anchors**:
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#comparator-and-estimand-contract`
  - `explains` → `paper/icems2026/working/chapter_blueprint.md#vi-limitations`
