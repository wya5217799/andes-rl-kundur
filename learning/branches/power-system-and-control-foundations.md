# `Power-System and Control Foundations | 电力系统与控制基础`

## `Power Imbalance | 功率不平衡`

- **Type**: `Foundation`
- **Requires**: `None`
- **Used in**: `dynamic-mechanism`
- **Project role**: 为项目中发电机加减速、频率偏移和储能有功响应提供物理起点。
- **Anchors**:
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#executable-gencls-and-esd1-equations`

## `Swing Equation | 摆动方程`

- **Type**: `Foundation`
- **Requires**: `Power Imbalance`
- **Used in**: `dynamic-mechanism`, `simulation-implementation`
- **Project role**: 把净功率或转矩不平衡连接到转速变化，是项目动态模型的核心关系。
- **Anchors**:
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#executable-gencls-and-esd1-equations`

## `Rotor-Angle Dynamics | 转子角动态`

- **Type**: `Foundation`
- **Requires**: `Swing Equation`
- **Used in**: `physical-system`, `dynamic-mechanism`
- **Project role**: 解释发电机转速偏差如何积累成角度变化并影响区域间动态。
- **Anchors**:
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#executable-gencls-and-esd1-equations`

## `Synchronizing Coupling | 同步耦合`

- **Type**: `Foundation`
- **Requires**: `Rotor-Angle Dynamics`
- **Used in**: `physical-system`, `dynamic-mechanism`
- **Project role**: 解释电气网络如何把不同发电机和区域的角度运动连接起来。
- **Anchors**:
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#common-differential-and-graph-coordinates`

## `Coherent Generator Motion | 发电机相干运动`

- **Type**: `Foundation`
- **Requires**: `Rotor-Angle Dynamics`, `Synchronizing Coupling`
- **Used in**: `dynamic-mechanism`
- **Project role**: 支撑把多台机器理解为区域内近似同向运动的群体，而不是彼此无关的单机。
- **Anchors**:
  - `explains` → `paper/icems2026/working/chapter_blueprint.md#ii-decoupled-control-problem`

## `Inter-Area Oscillation | 区域间振荡`

- **Type**: `Foundation`
- **Requires**: `Coherent Generator Motion`, `Synchronizing Coupling`
- **Used in**: `physical-system`, `dynamic-mechanism`, `experimental-validation`
- **Project role**: 说明两个机器群为何会发生相对摆动，也是项目选择两区域系统的主要可解释机制。
- **Anchors**:
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#topology-decision-and-claim-ceiling`

## `Kundur Two-Area Benchmark | Kundur 两区域基准系统`

- **Type**: `Foundation`
- **Requires**: `Inter-Area Oscillation`
- **Used in**: `physical-system`, `experimental-validation`
- **Project role**: 为项目提供具有明确区域间机制的固定相量域实验载体，而不是拓扑新颖性证据。
- **Anchors**:
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#topology-decision-and-claim-ceiling`
  - `explains` → `paper/icems2026/working/chapter_blueprint.md#iv-prospective-experiment`

## `Center-of-Inertia Frequency | 惯性中心频率`

- **Type**: `Foundation`
- **Requires**: `Rotor-Angle Dynamics`
- **Used in**: `dynamic-mechanism`, `control-architecture`
- **Project role**: 提供多机整体频率运动的惯量加权坐标，是共模频率定义的物理基础。
- **Anchors**:
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#common-differential-and-graph-coordinates`

## `Common-Mode Frequency | 共模频率`

- **Type**: `Foundation`
- **Requires**: `Center-of-Inertia Frequency`
- **Used in**: `dynamic-mechanism`, `control-architecture`
- **Project role**: 表示多台受控设备共同升降的整体频率分量，用于区分净功率支持与相对分配。
- **Anchors**:
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#common-differential-and-graph-coordinates`

## `Differential-Mode Frequency | 差模频率`

- **Type**: `Foundation`
- **Requires**: `Coherent Generator Motion`
- **Used in**: `dynamic-mechanism`, `control-architecture`
- **Project role**: 表示设备或区域之间的相对频率运动，用于描述同步和分配问题。
- **Anchors**:
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#common-differential-and-graph-coordinates`

## `Common–Differential Decomposition | 共模—差模分解`

- **Type**: `Foundation`
- **Requires**: `Common-Mode Frequency`, `Differential-Mode Frequency`
- **Used in**: `control-architecture`, `simulation-implementation`
- **Project role**: 把整体频率支持与相对同步分配分成可辨认但仍可能耦合的控制坐标。
- **Anchors**:
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#common-differential-and-graph-coordinates`

## `Control-Objective Separation | 控制目标分离`

- **Type**: `Foundation`
- **Requires**: `Common–Differential Decomposition`
- **Used in**: `control-architecture`, `experimental-validation`
- **Project role**: 解释项目为何分别验证共同支持、差分分配和受限残差，而不是把所有控制作用混成一个目标。
- **Anchors**:
  - `explains` → `paper/icems2026/working/chapter_blueprint.md#ii-decoupled-control-problem`
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#deterministic-and-neural-controller`
