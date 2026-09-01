# Data guide

The archive intentionally includes enough exact data to audit and replay a
representative actor path, plus compact full-grid summaries. It does not include
all 24 checkpoints or all 836 R485 trace files.

## Authority order

1. `formal/r485_formal_analysis.json` and `claims/CLM-1525.md`;
2. `formal/r486_analysis.json` and `claims/CLM-1530.md`;
3. the five post-hoc result JSONs and their exact probe code;
4. representative checkpoint and trace data;
5. paper-facing digests and briefs.

## Machine-readable data

| Archive entry | Purpose |
|---|---|
| `formal/r485_formal_analysis.json` | Full formal R485 decision, qualification counts, guards, source inference, and deterministic gates. |
| `formal/r486_analysis.json` | Durable post-hoc intake and promoted numerical summaries. |
| `posthoc/projection_tv_result.json` | First policy, four profiles: raw/projected/direct-MD TV and exact projector checks. |
| `posthoc/reward_tv_blindness_result.json` | Same action row multisets under temporal reordering: identical registered action cost, different TV. |
| `posthoc/feedback_grid_result.json` | 24-policy, one-profile fixed-previous-input raw-TV grid, including every policy row. |
| `posthoc/quasistatic_rms_grid_result.json` | 24-policy x four-profile constant-anchor RMS grid, including all 96 rows and 192 channel ratios. |
| `posthoc/recursive_intervention_result.json` | Representative four-profile recursive projector intervention and direct-MD comparisons. |

## Representative replay data

- `checkpoint/an_cn_r0_seed501_final.pt`: four actor members and their metadata;
  SHA-256 `c5fec5e301cae22fbc71818523aca119d85bcb304b42f4dc87043618b072aaaa`.
- `traces/canary_eval_[a-d].json`: each has six records x 150 steps, with
  canonical observations, raw actions, projected/executed actions, and
  checkpoint lineage.
- `source/networks.py` and `source/executed_action_sac.py`: exact actor and
  projector/training-interface implementation.
- `probes/*.py`: the exact deterministic computations that produced the
  attached post-hoc JSONs.

The representative actor can be loaded with Python/PyTorch using
`torch.load(..., map_location="cpu", weights_only=True)`. Each of the four
members is reconstructed as `GaussianActor(9, 2, [128,128,128,128])` and loaded
from `member["actor"]`.

## Deliberately absent objects

- The other 23 binary checkpoints and their full raw traces are omitted for
  portability. Their exact finite-grid outputs are present in the result JSONs.
- No modified-controller plant observations exist. Therefore no attached file
  identifies a closed-loop counterfactual observation path.
- No random-sampling design or superpopulation model exists for the 24-policy
  grid.
- No actuator wear, energy, thermal, damage, or hardware-safety state exists in
  R485.

If a claimed theorem or numerical certificate needs an absent object, return
`DATA-UNDECIDABLE` for that part and name the minimal missing data. Do not
substitute a looser but differently defined object without marking it as a new
assumption.
