# R402 causal-audit deliverables

This package contains a source-bounded causal audit of the R402 MARL canary failure. It uses the numerical values and evidence boundaries stated in the supplied Markdown problem package. It does **not** independently verify the repository hashes or regenerate ANDES trajectories because the named repository artifacts were not supplied.

## Main deliverables

- `r402_causal_audit_report.md` — complete 12-section audit, causal DAG, mechanism classification, multiplier/optimization/message analyses, DAE authority framework, minimum-evidence matrix, and manuscript-ready English.
- `r402_recompute.py` — deterministic arithmetic and consistency checker.
- `r402_authority_tools.py` — prospective index-1 DAE reduction, ZOH discretization, lifted finite-horizon response, Gramian, decoder-slope, slew, and actor-gradient utilities.
- `r402_audit_input.json` — machine-readable transcription of the stated numerical inputs.
- `generated/r402_audit_recomputed.json` — computed counts, ratios, contrasts, bounds, and unit-of-analysis warnings.
- `*.csv` and `generated/*.csv` — structured audit tables and recomputed numerical tables.
- `test_r402_tools.py` — lightweight self-tests.
- `SHA256SUMS` — checksums for this generated package.

## Reproduce the arithmetic

```bash
python r402_recompute.py \
  --input r402_audit_input.json \
  --outdir generated
```

Expected key output:

```text
total_files = 40
total_trajectories = 240
learning_trajectories = 216
deterministic_trajectories = 24
action_component_samples_per_arm_seed = 5760
```

## Run self-tests

```bash
python test_r402_tools.py
```

## Use the DAE/authority tools

The authority module requires actual project matrices before any output can be treated as plant evidence. At minimum, supply per-operating-point `f_x`, `f_y`, `g_x`, `g_y`, action-specific `f_u`, `g_u`, disturbance/output Jacobians, decoder/headroom derivatives, and a matched comparison contract.

```python
from r402_authority_tools import reduce_index1_dae, zoh_discretize

reduced = reduce_index1_dae(
    f_x=fx,
    f_y=fy,
    f_u=fu_md,
    g_x=gx,
    g_y=gy,
    g_u=gu_md,
)
A_d, B_d = zoh_discretize(reduced.A, reduced.B_u, dt=0.2)
```

## Dependencies

- Python 3.10+
- NumPy
- pandas
- SciPy

No simulator, training, bank reopening, algorithm sweep, or external web data is used by the recomputation script.
