# `Modeling and Evidence Foundations | 建模与证据基础`

## `Operating Point | 运行点`

- **Type**: `Foundation`
- **Requires**: `Power Imbalance`
- **Used in**: `dynamic-mechanism`, `simulation-implementation`
- **Project role**: 给线性化、局部模型和受控对比提供共同参考状态，避免把不同平衡条件下的响应直接混合。
- **Anchors**:
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#exact-plant-boundary`

## `Differential-Algebraic Equation | 微分代数方程`

- **Type**: `Foundation`
- **Requires**: `Swing Equation`, `Operating Point`
- **Used in**: `dynamic-mechanism`, `simulation-implementation`
- **Project role**: 解释动态状态与网络瞬时约束为何必须联合求解，是模型优先路线理解完整电网模型的入口。
- **Anchors**:
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#exact-plant-boundary`

## `Small-Signal Linearization | 小信号线性化`

- **Type**: `Foundation`
- **Requires**: `Differential-Algebraic Equation`, `Operating Point`
- **Used in**: `dynamic-mechanism`, `simulation-implementation`
- **Project role**: 在一个运行点附近用局部线性关系近似非线性电网动态，为模态、耦合和预测模型分析提供入口。
- **Anchors**:
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#exact-plant-boundary`

## `Schur-Complement Reduction | Schur 补消元`

- **Type**: `Foundation`
- **Requires**: `Small-Signal Linearization`
- **Used in**: `dynamic-mechanism`, `simulation-implementation`
- **Project role**: 消去网络代数变量并保留其对动态状态和控制输入的影响，而不是把网络耦合直接忽略。
- **Anchors**:
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#exact-plant-boundary`

## `Sampled-Data Control | 采样数据控制`

- **Type**: `Foundation`
- **Requires**: `Differential-Algebraic Equation`, `Active-Power Control Channel`
- **Used in**: `control-architecture`, `simulation-implementation`
- **Project role**: 说明离散控制器、保持不变的命令与连续电网动态如何按固定时序交互。
- **Anchors**:
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#sampled-update-order`
  - `explains` → `paper/icems2026/working/chapter_blueprint.md#iv-prospective-experiment`

## `Input–Disturbance Separation | 输入—扰动分离`

- **Type**: `Foundation`
- **Requires**: `Small-Signal Linearization`, `Active-Power Control Channel`
- **Used in**: `simulation-implementation`, `experimental-validation`
- **Project role**: 把控制器主动施加的功率与外部负荷扰动分成不同通道，避免预测器把两种因果来源混为一体。
- **Anchors**:
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#r341-handoff-and-external-advisory-disposition`

## `Reduced-Order Predictor | 降阶预测模型`

- **Type**: `Foundation`
- **Requires**: `Schur-Complement Reduction`, `Sampled-Data Control`, `Input–Disturbance Separation`
- **Used in**: `control-architecture`, `simulation-implementation`, `experimental-validation`
- **Project role**: 在保留关键动态、控制通道和扰动通道的同时降低模型规模，为确定性控制器提供可计算预测。
- **Anchors**:
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#modeling-and-simulation-workflow`

## `Residual Improvement Headroom | 残差改进余量`

- **Type**: `Foundation`
- **Requires**: `Deterministic Control Backbone`, `Residual Control`, `Action Headroom`, `Matched Comparator`
- **Used in**: `research-question`, `experimental-validation`, `evidence-and-paper-claim`
- **Project role**: 判断确定性控制之后是否仍存在既安全又可测量的改进空间，从而决定训练学习残差是否值得。
- **Anchors**:
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#modeling-and-simulation-workflow`
  - `explains` → `paper/decoupling_marl_model_first/working/model_contract.md#training-and-eval-gates`
