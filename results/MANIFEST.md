# results/ Manifest

This directory is gitignored except for `whitelist/` (paper-cited checkpoints
and eval JSON) and this manifest itself.

## Why

Training artifacts can reach GB scale per round. Storing everything in git would
bloat the repo and slow clones. The whitelist contains only what the paper
directly cites; everything else is local-only.

## Current SCI experiment evidence (pointer-only)

Archive status: **LOCAL-ONLY**. The following roots exist on this workstation,
but no private second-copy locator is registered. This table preserves paths
and decision-artifact digests only; it does not make the ignored data
recoverable and does not authorize a public push. Register a private backup
locator before calling these artifacts durably archived.

| Round | Result root | Decision artifact | SHA-256 |
|---|---|---|---|
| R281 | `results/r281_eig_mechanism/` | `summary.json` | `06344bfa07e014b69fa68785172bd08c6f5c957c2afda3230612790e8d27a559` |
| R282 | `results/r282_eig_upturn/` | `summary.json` | `00a2e3305d02aa0ae49e20e401008c2b2d24e0162c2387f66b96ff7c07850069` |
| R283 | `results/r283_strength_sweep/` | `branch_analysis.json` | `711bb421deb0fc554585e6c70b7291a5e2577c56568d8e8404f743b0a585513e` |
| R284 | `results/r284_eig_left_flank/` | `summary.json` | `dbb54964421855737b57427e27d1c3a3dd2b84f5931a3a990c170d16dec60ec5` |
| R285 | `results/r285_hybridization_map/` | `zone_analysis.json` | `74a110eb1618ae8850cf39c955addff991e238a194d19a0039872e57c712d7f9` |
| R286 | `results/r286_weak_grid_td/` | `weak_tie_summary.json` | `c1487c706a754e977a73763f00219e78f27ebaabcaecfbcc90bd9780dc111139` |
| R287 | `results/r287_weak_grid_stress/` | `weak_tie_summary.json` | `2dabeeb4fb9a1aafade7d8aa2126ce678069f1a868a0fb89b6f15212e7a3a129` |
| R288 | `results/r288_topology_information/` | `topology_inventory.json` | `ccf52b98fc082f3469950dd7895741e4b366cabaf9b75e96bf3204c3cc8ce7a2` |
| R289 | `results/r289_topology_information/` | `analysis.json` | `6e1164ad47397e9bf406c84fcb4a465a1e2db7e8267c410fdd33161e528a0a81` |
| R290 | `results/r290_topology_initialization/` | `diagnostic.json` | `9a7c3ea80ff4b2f73ba23d22ca60a1f7598dcf4d810c6a1c407ea3f750e45210` |
| R291 | `results/r291_state_aware_handoff/` | `formal_summary.json` | `87e1cf1f7c39e32bfbdc6ca2a9e379cbf3e212c0198781cc39c286e2c08f6cd0` |
| R292 | `results/r292_formal_evaluation_v3/` | `formal_summary.json` | `3d60c73a771f3a22df813ff06a9bcd740707b86cff9667d6e24785a120e6ac1b` |
| R294 | `results/r294_model_validation/` | `round_summary.json` | `6ec979d146abc553b3e87599f0736d2ab937f504e1cd2d617eef8208bbb184b3` |
| R295 | `results/r295_consensus_timescale_probe/` | `development_summary.json` | `3fcb51396f6aabffe4bbea5e38fa586292ce4cc8abc8499c35f66439e361979c` |
| R296 | `results/r296_relative_rocof_probe/` | `development_summary.json` | `be6a58a301db57349e1a1328c5e3e14ba0f26c5ee1546e5f0f918ef2a4ef3cb1` |
| R297 | `results/r297_relative_rocof_amplitude/` | `development_summary.json` | `2e1f5307ec79cf6fb32e06f043fd630f4608275ec600ad045d8780b1814bf07d` |
| R298 | `results/r298_relative_rocof_formal/` | `formal_summary.json` | `df56c1a72e292191c3c769950aa876b58fce3f73de83edb44ae7a7e3a51f8728` |
| R299 | `results/r299_edge_information_probe/` | `development_summary.json` | `33df4ced90b50ddc5b6f91122914204baed4a862efde841d55364a7906b3fec7` |
| R300 | `results/r300_fixed_2kv_formal/` | `formal_summary.json` | `07502f6c67e2a4f47042362b3c6136b8f75412f80a3a8f1df08d2b4601fc2f37` |
| R301 | `results/r301_relative_rocof_margin/` | `analysis_summary.json` | `3b97453ada0f8d5b6560fa20ec166c84799d1f45e98fb1ab502f53b20962a5e9` |
| R302 | `results/r302_vector_eval_training_gate/` | `analysis_summary.json` | `2efb733b79a78ab5c895a3ddb15e8139cb3b6ccf67c28359e45ddcd202e8d36f` |
| R303 | `results/r303_projection_coupling/` | `analysis_summary.json` | `44e178609c2a18ed631bee609f113f01cfd079c0ccb78b53dedd2d4deabc1781` |
| R304 | `results/r304_topology_vector_gate/` | `analysis.json` | `6197e0abfb388618d999d91495e4162158cbb3ad9c5c4d7cc968a42bb641c827` |
| R305 | `results/r305_topology_vector_gate/` | `analysis.json` | `aecee35c5eea59f9a24ad38eb31217ec0ce4cacd2cb057e0af75d6685ec6ec3f` |
| R306 | `results/r306_model_first_stage0/` | `analysis.json` | `9dff6dec44041c6b2eb60787fde6ab6f5916d8e91d880bdb15c1350f53d42efd` |
| R307 | `results/r307_model_first_stage1/` | `analysis.json` | `8bafeaee16f3c8227e93e0243b7607df772d11da5313c5e8c87904c9f579eae0` |
| R308 | `results/r308_model_first_tds_canary/` | `analysis.json` | `9c837a3eec44a5c2ee22efdd2d33a879cad7b7d8efcb217fa4397b1441525160` |
| R309 | `results/r309_model_first_two_phase_tds_canary/` | `analysis.json` | `c0993c6961b92005bc01a4c001d7d8edfd088f9bf69310ca869a343fe7718e70` |
| R310 | `results/r310_model_first_stage1/` | `analysis.json` | `261a50b93300a7e628a4cd9b3eb71f1fa20a23a82a07e2e0c859781c77606d65` |
| R311 | `results/r311_model_first_eval_guard_canary/` | `analysis.json` | `488d17b3e792641bcdcab00ef1a4b4e0c8ecf95eb35d5ce6bb48377f12266b44` |
| R312 | `results/r312_model_first_stage1/` | `analysis.json` | `75804e5fb3f704a3d0b878db20819f997c15aaa46ae6d6dcc886879eea361c02` |
| R313 | `results/r313_model_first_predictor/` | `analysis.json` | `65c3cdbaffa92f9c82cc52775cc2ab472501b421102e6a44f0972edf760ff299` |
| R314 | `results/r314_local_predictor/` | `analysis.json` | `bfe177502d3dddf4b2bb1d2d8532f45ea14f2e7471601623a26de9108e865ead` |
| R315 | `results/r315_dynamic_reduction/` | `analysis.json` | `12e44f04c1941663c2037e57db6cc1c4f0b76314db3ff14bac67b8eced209b0a` |
| R316 | `results/r316_dynamic_reduction/` | `analysis.json` | `a8c0f1ec0ce03a9a08da4f47cd661e921bebf7461154bf1ebece175a68368b7c` |
| R317 | `results/r317_offline_controller/` | `analysis.json` | `fbb85b20f97fbb1e8ff4d3d03325c1fa84192cd1adf9e4e75707d755b9d19318` |
| R318 | `results/r318_rejection_diagnosis/` | `analysis.json` | `7d76895ca5f351a75f29e3ef876e20257b51fff0c0f88012f08f86584e3dfd8a` |
| R319 | `results/r319_observer_lqr/` | `analysis.json` | `a7c5b811dfc9d5ef4c2095bfad326e8d241d2e2762d9576f6f6e8f28707abe3e` |
| R320 | `results/r320_pole_cause/` | `analysis.json` | `f17642e819c9b898e2e7d9866e6d06699575f7f14799347f88743919a8495177` |
| R321 | `results/r321_pole_target_examination/` | `analysis.json` | `03c0f7ea7d5e530b4a947b768aaab0162d88ae3c06e8629815cb6149640e0ea6` |
| R322 | `results/r322_feedback_diagnosis/` | `analysis.json` | `1929306a1237c526518abce542f2badbf7e44aac58a8564c544a4a43dc5c6674` |
| R324 | `results/r324_model_fidelity/` | `analysis.json` | `6736862f964872cbd985e6279556f239adc6a42051b8bd1a9ccd8c7e22c6536b` |
| R325 | `results/r325_constrained_horizon/` | `analysis.json` | `ff25ef1cc01332b2fd8295f36288896abb33cdd4d21751250bb40e26c54cdfe4` |
| R326 | `results/r326_solver_adequacy/` | `analysis.json` | `066df82be6c2815dcb6feefa25ed26e0c9434fb96eb68fd3993c9e4f630486e0` |
| R327 | `results/r327_reference_recovery/` | `analysis.json` | `6165b7f950bffe4f820825b39607d20473c79de825d8efe0eb68538c2c5dc13e` |
| R328 | `results/r328_estimation_cause/` | `analysis.json` | `bc514a69b62269752bb5fa9e4c4fbc1c1e8df04db72c929986e63b60a6670cb9` |
| R329 | `results/r329_disturbance_estimator/` | `analysis.json` | `5c2a7bc9cbde1595bee2def418a13c13a60cb378d1db12b0baeb4f8ca539ca74` |
| R330 | `results/r330_estimator_holdout/` | `analysis.json` | `cd0fbf9ad57c842cbfdf786819ab6f0eef95277f3f79b05ee1b64d7558bcd33c` |
| R331 | `results/r331_andes_bridge_reconciliation/` | `analysis.json` | `1c4f3af91b961c796b6e54c18e3c23a4fe67aa37e753c2d9261872254d3e3353` |
| R332 | `results/r332_andes_bridge_reconciliation/` | `analysis.json` | `dd763fad864e82fceaff5af83168d9d4a379408c2367f7b61a1729bd092dc928` |
| R333 | `results/r333_pq_disturbance_identification/` | `analysis.json` | `39d5f7be9f3280aea28c5c5e57a42b0c46811e6002758fddf64ab981878d36c1` |
| R334 | `results/r334_pq_disturbance_identification/` | `analysis.json` | `453ada22907526f571a4099295b9a9e9056b5a81fc286e0af0f0084f7dd4c86f` |
| R336 | `results/r336_disturbance_package/` | `analysis.json` | `86cda073ea6f9e263967e91ed14bb4719411591fc29c0e20aaffbedacd4666fb` |
| R338 | `results/r338_formal_evaluation/` | `formal_summary.json` | `2aeff9b8016e92b282214908b3f0c5aa07bd028baadbc0ada0340c8c52d1cf04` |
| R339 | `results/r339_input_bridge_diagnosis/` | `analysis.json` | `60c1ae995759c41919b31eb924ae22025d3d1140d5bac9190bf9cf823c9dab9d` |
| R340 | `results/r340_fresh_model_validation/` | `validation_failure.json` | `a62a8865eb9c14ac8ca5f90973bc3ee31c024dfddc8dd29077f9cac044a7a4f1` |
| R341 | `results/r341_staged_fresh_model_validation/` | `analysis.json` | `f68b4f98399c804670e6f2e80d65dc6bda3cc0cccc1da5ac5d437a9bb1c73ac9` |
| R344 | `results/r344_deterministic_bridge/` | `formal_analysis.json` | `41c8e73deadbf30d0352dc5a20f82938ad3723ca7f2467a86f2d8f494996ad72` |
| R350 | `results/r350_smooth_convex_residual/` | `analysis.json` | `81801fd7e2d90b6aa231a887c13b4ded838e4392a0b112cff594a8278c418e32` |
| R351 | `results/r351_matched_distributed_bridge/` | `analysis.json` | `8dd75b25ad1c28e9df2334df1e3494cdffb883837ba88462d77da66f42be5e65` |
| R352 | `results/r352_distributed_controller_loop_v2/` | `formal_analysis.json` | `c4533ed29a9c5f7e39430f84c9c65d11b95f1fd4379cbccb1a76597b07f79a8e` |
| R356 | `results/r356_joint_endpoint_feasibility/` | `analysis.json` | `9a4334c4575cd803114e52c4ed2279efe6defa979734b08e3bc28de0e37332b1` |
| R357 | `results/r357_physical_joint_endpoint_feasibility/` | `failure.json` | `933ea85ca6b753fe1bfaf72ab674427d68f1dee8b1acb2911f3a0aeb010a77fb` |
| R358 | `results/r358_physical_joint_endpoint_qp/` | `analysis.json` | `c471aafc51a3019202777ca166e66b7c93739304fcd335bbe1511a5b3f4f26fb` |
| R359 | `results/r359_neighbour_causal_residual/` | `analysis.json` | `aa5b1d89d238a68f5b3c5506319a66450fdaa23b4f207894a3b7bd2fb4832f0f` |
| R360 | `results/r360_flexible_neighbour_residual/` | `analysis.json` | `2a87258e37a52578d1bb339542054d6055c1e534378078e4b6afe53687e61ffc` |
| R361 | `results/r361_neighbour_message_residual/` | `analysis.json` | `279f5aa53cfeccca658b4359441d735079da04712fd648430fa088edf320677f` |
| R362 | `results/r362_shared_prediction_residual/` | `analysis.json` | `bcad59b38032ef8bb33293711897e06bc5a8e023f52763afcfcb640bfec14fc1` |
| R363 | `results/r363_common_channel_qp/` | `analysis.json` | `acc805c0cb2b4a90997f9a410f1af6187fe78bf254576326dc17c649f5d00238` |

The sixty-three roots currently occupy 698,059,785 bytes. R286, R287, R291, R292,
R294, R295, R296, R297, R298, R299, and R300 raw traces remain ignored; their retained trace hashes are indexed by
each round's decision and provenance artifacts.

Integrity note: the 12 JSON files under R281-R285 received non-overwriting
`.sha256` sidecars on 2026-07-30. These are
`retrospective-current-snapshot` checksums for future byte-drift detection,
not prospective seals or evidence of the original execution time. R286 and
later round artifacts were emitted with sidecars by their execution workflow.

## How to bring local artifacts in

Sibling local directory (not committed) contains the full training results.
Symlink or copy as needed:

```powershell
# Example: bring R21 best.pt from the source repo
$SRC = "C:\Users\27443\Desktop\Multi-Agent  VSGs\results"
$DST = "C:\Users\27443\Desktop\andes-rl-kundur\results"
Copy-Item "$SRC\<run_dir>\best.pt" "$DST\<run_dir>\"
```

## Whitelist contents

| Path | Source | Cited by | Notes |
|------|--------|----------|-------|
| `whitelist/andes_paper_alignment_6axis_2026-05-07.json` | r30 ranker fix re-rank | paper §V-A, §V-B | post-fix headline ranking (CLM ledger source) |

(Update this table when adding files to whitelist/.)

## What is NOT in whitelist

- Per-step trajectory dumps from training runs
- Per-seed full result trees (e.g., `andes_dfloor_seed42/`)
- Intermediate ensemble eval JSON files
- Smoke test logs

These are reproducible from the code in this repo + the artifacts in the source
repo. If a future paper or revision needs to cite them, add to whitelist.
