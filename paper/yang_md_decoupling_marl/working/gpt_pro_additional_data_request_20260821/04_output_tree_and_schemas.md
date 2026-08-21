# 建议输出目录与字段规范

## 目录树

```text
u1_u9_truth_evidence_<date>/
├── README.md
├── provenance/
│   ├── reproduction_manifest.json
│   ├── input_inventory.json
│   ├── commands.jsonl
│   ├── environment.txt
│   ├── git_diff.patch
│   └── source_hashes.json
├── contracts/
│   ├── object_registry.json
│   ├── units_and_coordinates.json
│   ├── profile_protocol.json
│   ├── guard_contract.json
│   └── claim_evidence_map.json
├── model_exports/
│   ├── object_a/
│   │   ├── dae_snapshot.npz
│   │   ├── input_output_maps.npz
│   │   ├── execution_contract.json
│   │   └── metadata.json
│   └── object_b/
│       ├── dae_snapshot.npz
│       ├── continuous_reduced_model.npz
│       ├── sampled_model.npz
│       ├── controllers.npz
│       ├── headroom_modes.json
│       └── metadata.json
├── u1_certificate/
│   ├── class_contract.json
│   ├── dcf_factors.npz
│   ├── bezout_check.json
│   ├── lift_arrays.npz
│   ├── lift_index.json
│   ├── phase1_problem.npz
│   ├── solver_log.txt
│   ├── primal_solution.npz
│   ├── dual_solution.npz
│   ├── certificate_check.json
│   └── nonlinear_validation/
├── u2_factorial/
│   ├── preregistration.json
│   ├── power_analysis.json
│   ├── donor_bank/
│   ├── placebo_audit.json
│   ├── arm_contracts.json
│   ├── seeds/
│   ├── paired_contrasts.json
│   └── classification.json
├── u3_u4_traces/
│   ├── trace_metadata.json
│   ├── transitions.parquet
│   ├── target_audit.parquet
│   ├── guard_recomputation.json
│   ├── training_constraint_trace.parquet
│   └── phase1_guard_feasibility/
├── u5_u8_math/
│   ├── u5_total_sensitivity/
│   ├── u6_fractional_delay/
│   ├── u7_bilinear_tensors/
│   └── u8_cross_separation/
├── r458/
│   ├── frozen_inputs/
│   ├── development/
│   ├── selection.json
│   ├── evaluation/
│   └── formal_analysis.json
├── independent_checks/
│   ├── verify_all.py
│   ├── recompute_endpoints.py
│   ├── check_certificate.py
│   └── verification_report.json
└── SHA256SUMS
```

## `object_registry.json`

```json
{
  "schema_version": 1,
  "objects": {
    "A": {
      "actuator_type": "multiplicative-MD",
      "agents": 4,
      "action_dim_per_agent": 2,
      "physical_output_base_hz": 60.0,
      "model_base_hz": 50.0
    },
    "B": {
      "actuator_type": "additive-energy-port",
      "control_channels": 4,
      "disturbance_channels": 3,
      "frequency_outputs": 4,
      "physical_output_base_hz": 60.0,
      "model_base_hz": 50.0
    }
  }
}
```

必须扩展为真实字段；示例不得直接当结果。

## `units_and_coordinates.json`

必须至少包含：

```text
state_names, state_units
algebraic_names, algebraic_units
control_names, control_units
 disturbance_names, disturbance_units
output_names, output_units
input_scale_matrix
output_scale_matrix
frequency_offset_hz
common_basis
registered_T_d
projector_convention
sample_observation_timing = pre-step | post-step
```

## Object B `sampled_model.npz`

建议键：

```text
A_d              (n,n)
Bc_d             (n,4)
Bw_d             (n,3)
C_pre            (4,n)
D_pre_control     (4,4)
D_pre_disturbance (4,3)
C_post            (4,n)
D_post_control    (4,4)
D_post_disturbance(4,3)
Ts                scalar
state_gauge_basis (n,k)
state_keep_basis  (n,n-k)
```

Object B 当前预期 `n=102`，但 checker 应从文件 shape读取，不要硬编码后掩盖漂移。

## `class_contract.json`

```json
{
  "schema_version": 1,
  "class_id": "QY10-differential-frobenius-1",
  "route": "verified-dcf-youla",
  "tap_indices": [1,2,3,4,5,6,7,8,9,10],
  "strictly_causal": true,
  "basis": "registered_T_d",
  "free_matrix_shape_per_tap": [3,3],
  "free_variable_count": 90,
  "coefficient_constraint": "sum_frobenius_squared_le_1",
  "normalization_contract_sha256": "...",
  "locality_claim": false,
  "feedback_sign": "u=-Ky"
}
```

## `lift_index.json`

每个 response row：

```text
row_id
object_id
profile_id
scenario_id
metric_id
sample_index
physical_time_s
output_channel/projected_coordinate
unit
weight
reference_id
active_mode_id
```

每个 variable column：

```text
column_id
tap_h
qhat_row
qhat_col
physical_Q_mapping
```

`lift_arrays.npz` 至少含：`A_response,b_response,variable_basis`，另存每类 guard 的 row slices。

## `certificate_check.json`

```json
{
  "status": "FEASIBLE-WITNESS-IN-QY10 | INFEASIBLE-QY10-WITH-VERIFIED-DUAL-BOUND | CERTIFICATE-INVALID | CERTIFICATE-NOT-IDENTIFIABLE",
  "bezout_relative_residual": 0.0,
  "primal_equality_residual": 0.0,
  "maximum_cone_violation": 0.0,
  "dual_stationarity_residual": 0.0,
  "relative_duality_gap": 0.0,
  "dual_lower_bound_unscaled": null,
  "numerical_error_allowance": 0.0,
  "nonlinear_discrepancy_allowance": 0.0,
  "high_precision_verified": false,
  "checker_source_sha256": "..."
}
```

无结果时使用 `null` 和明确 reason，不得填 0。

## 逐步 transition schema

推荐 Parquet，每行一个 joint transition。详细字段见 `templates/TRACE_SCHEMA.md`。数组列可使用固定 shape list；同时在 metadata 里保存 shape、dtype、channel labels。

## U5 derivative bundle

`u5_total_sensitivity/parameter_points.json` 每点：

```text
parameter_name
log_parameter_offset
M_values,D_values
equilibrium_hash
equilibrium_residual
active_mode_hash
continuous_model_hash
sampled_model_hash
controller_hash
reference_hash
```

`frequency_arrays.npz`：

```text
frequency_hz
z_points
Pc,Pw,K,L,S,G
Pc_rho,Pw_rho,K_rho,L_rho,S_rho,G_rho
cond_zI_minus_A
cond_I_plus_L
energy_integrand
energy_derivative_integrand
```

## U6 branch table

每个 delay/eigen branch：

```text
tau_s, integer_delay_samples, fractional_delta_s
branch_id, eigenvalue_real, eigenvalue_imag, modulus
left_right_overlap, eigen_residual, branch_match_score
is_gauge, is_simple, crossing_bracket_id
augmented_matrix_sha256
```

## U7 tensor bundle

`mixed_tensors.npz`：

```text
N  (8,n,n)
E  (8,n,r)
R  (8,p,n)
S  (8,p,r)
```

若只导出 JVP/HVP，则必须有 `directions.npz` 和明确的 operator API/checker，不能把方向数据称为完整 tensor。

## U8 projector 与 bound

`projectors.npz`：

```text
P_u,Q_u,P_y,Q_y
P_x,Q_x   # 仅在可验证时存在
T_common,T_differential
```

`bound_table.parquet` 每 frequency/profile 至少：

```text
epsilon_A,epsilon_B,epsilon_C,epsilon_D
resolvent_norm
actual_cross_norm
upper_bound
bound_slack
sigma_min_Zdd
abs_Sc
mode/gauge flags
```

## `claim_evidence_map.json`

每个 claim：

```json
{
  "claim_id": "U7-local-quadratic-scaling",
  "scope": "Object A, registered equilibrium, fixed mode, finite horizon",
  "status": "supported | refuted | unresolved | invalid",
  "raw_inputs": [{"path":"...","sha256":"..."}],
  "derived_fields": [{"path":"...","json_pointer":"..."}],
  "scripts": [{"path":"...","sha256":"..."}],
  "independent_checks": [{"path":"...","status":"pass"}],
  "authorized_wording": "...",
  "prohibited_wording": ["..."]
}
```
