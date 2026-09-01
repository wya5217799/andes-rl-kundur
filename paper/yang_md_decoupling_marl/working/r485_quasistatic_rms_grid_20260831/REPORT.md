# R485 quasi-static RMS fixed-grid checkpoint replay

> Post-hoc actor-path diagnostic; no ANDES trajectory or training.

**Decision:** `QUASISTATIC_RMS_GRID_HETEROGENEOUS`

- Grid: 24 policies x 4 profiles = 96 blocks / 192 channel ratios.
- Ratio min / q05 / median / q95 / max: 0.701 / 0.802 / 0.959 / 1.073 / 1.195.
- Prevalence >= 0.90: 73.4%; prevalence <= 0.50: 0.0%.

| Profile | min | median | max | >=0.90 | <=0.50 |
|---|---:|---:|---:|---:|---:|
| canary_eval_a | 0.740 | 0.970 | 1.195 | 72.9% | 0.0% |
| canary_eval_b | 0.767 | 0.958 | 1.152 | 75.0% | 0.0% |
| canary_eval_c | 0.701 | 0.957 | 1.106 | 70.8% | 0.0% |
| canary_eval_d | 0.758 | 0.954 | 1.116 | 75.0% | 0.0% |

| Channel | min | median | max | >=0.90 | <=0.50 |
|---|---:|---:|---:|---:|---:|
| M | 0.701 | 0.915 | 1.195 | 56.2% | 0.0% |
| D | 0.813 | 0.987 | 1.152 | 90.6% | 0.0% |

The grid tests recurrence of retained raw RMS across fixed factors, seeds,
and profiles. It does not evaluate closed-loop endpoints, stability, or the
effect of retraining or modifying the controller.
