# `Project Foundation Map | 项目基础知识图`

- `research-question`
- `physical-system`
- `dynamic-mechanism`
- `control-architecture`
- `simulation-implementation`
- `experimental-validation`
- `evidence-and-paper-claim`

## Current learning branches

- [Power-System and Control Foundations](branches/power-system-and-control-foundations.md) — Kundur inter-area dynamics and common–differential control foundations.
- [Modeling and Evidence Foundations](branches/modeling-and-evidence-foundations.md) — DAE reduction, sampled prediction, causal channel separation, and residual-improvement headroom.
- [Control and Learning Architecture](branches/control-and-learning-architecture.md) — shared foundations plus the scalar-aggregation and independently executed vector-residual routes.

## Selected manuscript learning routes

- `icems2026`: `Common–Differential Decomposition` → `Fast–Slow Control Decomposition` → `Zero-Sum Action Constraint` → `Scalar Action Projection` → `Parameter Sharing` / `Centralized Action Aggregation` → `Matched Comparator` → `Causal Identifiability`.
- `decoupling-marl-model-first`: `Differential-Algebraic Equation` → `Small-Signal Linearization` → `Schur-Complement Reduction` / `Input–Disturbance Separation` → `Reduced-Order Predictor` → `Graph-Incidence Action Basis` / `Runtime Information Pattern` → `Independent Vector Action` / `Neighbour Message Passing` → `Decentralized Execution` → `Deterministic Control Backbone` → `Residual Control` / `Action Headroom` → `Governed Residual Control`; its evidence branch uses `Matched Comparator` → `Causal Identifiability`, while `Residual Improvement Headroom` joins the deterministic and matched-comparison paths.
