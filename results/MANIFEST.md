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
| R445 | `results/r445_gpt_pro_intake_verify/` | `analysis.json` | `a35445af7fbce3b4dd7003c788d9102bf2dd1b4e5dbcf9650da9aaa708f601ea` |
| R365 | `results/research_loop/r365_per_vsg_object_gate/` | `formal_analysis.json` | `3dde99211f8a685b04aa491787a9bcc0e869416637e206ac76319bc735b4986b` |
| R366 | `results/research_loop/r366_per_vsg_md_design/` | `analysis_v3.json` | `d8c29b9f5d523fbeae095c8efd827b5b2e044afa6e2061a1f396c5bae8f4f16e` |
| R367 | `results/research_loop/r367_deterministic_headroom/` | `formal_failure.json` | `4be0cc4e01a416035c3c5af13fba8c1c047e66b7c3e076bcc0db6c58c6ddda0f` |
| R368 | `results/research_loop/r368_deterministic_headroom/` | `formal_analysis.json` | `4b25f418f0c3b3fadf032d58cb0232f7ac69f5ea3a943a0e1dfbb99fb3264f6c` |
| R369 | `results/research_loop/r369_actuator_mapping_reanalysis/` | `analysis.json` | `e898cc452484f058d4f60cd43d1eca0f93ed0168d76062fa1fba90e08e01511f` |
| R371 | `results/research_loop/r371_vsg_energy_port_design/` | `analysis_v5.json` | `a068ec3756e834ba1f0c11d9c0736264e1ac81ca84c3bdc66ee3414caa531ca0` |
| R372 | `results/research_loop/r372_energy_port_object_gate/` | `formal_analysis.json` | `1268e7e92354b267d877e7590cb096c757773083a38070e8ec98035b3f72af6b` |
| R373 | `results/research_loop/r373_energy_port_authority/` | `formal_analysis.json` | `3392eb9b48702d88130cb27cdb24f7878dc9511e0b007aaa3223053194953b54` |
| R374 | `results/research_loop/r374_deterministic_decoupling/` | `formal_failure.json` | `61c32ace05929d55740539d9e4ca2a94e2db9153c189c0eabb4d97e387acc168` |
| R375 | `results/research_loop/r375_deterministic_decoupling_identity_correction/` | `formal_analysis.json` | `77e5f91053cd9437fd4922c8279d9fdf0175ed31d720532119611096732ba76c` |
| R376 | `results/research_loop/r376_gate_b_deterministic/` | `formal_analysis.json` | `db8c338f7c0b55f637f89388f3def10515be39b4e1f749a464d253044223af91` |
| R377 | `results/research_loop/r377_gate_b2_deterministic/` | `formal_analysis.json` | `7bd27756da8fe231565a4e52e8f49df0e1d1ad4ed9218a55feaa39a9c4d13f88` |
| R378 | `results/research_loop/r378_gate_b2_correction/` | `formal_analysis.json` | `af0395488440c183d7d0d48fd6ab9f0e66c9ea06d0b4f955116df51318aad1b2` |
| R379 | `results/research_loop/r377_gate_b3_deterministic/` | `formal_analysis.json` | `f6a8b4199626cebe4ad50c31f201948be71e6479dd43a1c80d2ba65663eb2ddb` |
| R380 | `results/research_loop/r380_vsg_source_model_gate/` | `formal_analysis.json` | `1503ed571b9d86ccf3c15af2ee679f5be7731e94f782e2bab0f9b5b2441b9de4` |
| R381 | `results/research_loop/r381_gate_b4_deterministic/` | `formal_analysis.json` | `696bd3c3f31e8b0e09ca3e8ff2af719b1094005dcb4863eddd3854892eec204d` |
| R382 | `results/research_loop/r382_bounded_headroom_witness/` | `formal_analysis.json` | `ddf1639bf8b14e89254f7b08da736fa97727d1b808594b31853bdc258cadd133` |
| R384 | `results/research_loop/r384_regcv1_object_gate/` | `formal_analysis.json` | `f9d92a165b10e2557810fa51da4c216cd2f5ccd5de2a9d14a0b10b5b022fa952` |
| R385 | `results/research_loop/r385_regcv1_clean_init_gate/` | `formal_analysis.json` | `9c84357586387de067630e0673c1aee08e05a010bd66d13be9c9be478f9aa0c8` |
| R386 | `results/research_loop/r386_regcv1_reference_capture_gate/` | `formal_analysis.json` | `16e0ea22e6703c3604013841c6d6e13fdaddf87f48ce1f39708879b15042a821` |
| R387 | `results/research_loop/r387_regcv1_signed_authority_gate/` | `formal_analysis.json` | `b44586e182e0208683a1d4ed67056c23fb860b7d3aa0163cad417ce42403b12e` |
| R388 | `results/research_loop/r388_regcv1_signed_authority_correction_gate/` | `formal_analysis.json` | `466296010670018e05619e2bd98a378c46f21d04cf74d0b01a2f4042215a5c39` |
| R389 | `results/research_loop/r389_regf2_object_init_gate/` | `formal_analysis.json` | `45d3a4cd7942ec509cf399b71bf4115417ac4a79985cdd250aad594f793d931e` |
| R390 | `results/research_loop/r390_regf2_equilibrium_eig_gate/` | `formal_analysis.json` | `a6a0bd51dec900ac978993aeba86347b1535e6b1e8b3a76f3b70e60382523d0e` |
| R391 | `results/research_loop/r391_regf2_equilibrium_eig_correction_gate/` | `formal_analysis.json` | `170658c967798aced2f4b62b614dd2863d2a8445ea4e92fbc2ac05968731619e` |
| R392 | `results/research_loop/r392_regf2_loop_perturbation_gate/` | `formal_analysis.json` | `e05da2d17c19d8d02012e4b8b1fc9d48b2ccb26d1af195bf9c3799fb7cb3ec8b` |
| R393 | `results/research_loop/r393_ppvsm1_object_gate/` | `formal_analysis.json` | `a2f525d9463421037c433518d68e07c4fdce04079d910d8f3be024aa1cb8f3c3` |
| R394 | `results/research_loop/r394_ppvsm1_object_gate/` | `formal_analysis.json` | `92a59571c4d704c7c655628d03048d444fe4e447e837731238b3b607d7752087` |
| R395 | `results/research_loop/r395_ppvsm1_object_gate/` | `formal_analysis.json` | `be209cb548352aa17aaa69608a2462db8ad0c61649f8ba5bb14bff10c8e6889a` |
| R396 | `results/research_loop/r396_ppvsm1_object_gate/` | `formal_analysis.json` | `b69847e30e6d2aee7f71dedfe7824a91a3fcc1b9591e4a5df906b3df454c916a` |
| R397 | `results/research_loop/r397_ppvsm1_signed_authority_gate/` | `formal_analysis.json` | `98f5afd48f8f2d5bd5743f5065ae7c1104298aa2bcb71fecdc223ae6966d5e6f` |
| R399 | `results/research_loop/r399_md_decoupling_headroom/` | `formal_analysis.json` | `03d8759f9417d382f3cc766d20f0a106cfc1822ba42a54d4d2659df1fb203088` |
| R402 | `results/research_loop/r402_cd_matd3_canary/` | `formal_analysis.json` | `1b65ff7789483d1f1c6e36fce86d1da88e02f54009aa82ef6657711a44d705b4` |
| R405 | `results/research_loop/r405_homogenization_gate/` | `formal_analysis.json` | `b608a586f16ef1aa9b54c08037a9637d3a29f5648a4a54a400d4afa26cf5393e` |
| R406 | `results/research_loop/r406_alpha_sweep/` | `formal_analysis.json` | `8bcde6cd1d8d85656b21fdf7c2de91ae96afab3bbd99295e25eea2b0a109c977` |
| R407 | `results/research_loop/r407_bandpass_gate/` | `formal_analysis.json` | `b5f698b8c838795faac263c6e66d777456b98672778ed2881d4f91f52058d460` |
| R410 | `results/research_loop/r410_message_repair/` | `formal_analysis.json` | `7f6244ab28d1c20a7b7fbf6eae0a8cbeed39825f1b96917bce6a845e165529b1` |
| R411 | `results/research_loop/r411_probe_amplitude_ladder/` | `formal_analysis.json` | `dde83a3bd1d39addacefe7d2111aa3e86b6c73497521d8d67aa90348fc219b29` |
| R413 | `results/research_loop/r413_topology_robustness/` | `formal_analysis.json` | `bc94e1fe35ed77e4a45aa189f3158a3c0c3178ebdad763cf8c340f963ca7fb9e` |
| R415 | `results/research_loop/r415_energy_port_extra_banks/` | `formal_analysis.json` | `58081cd4a990189b140ab4b114aa333fd18f7b8b7236d1dd2b969ef116e8502f` |
| R416 | `results/research_loop/r416_headroom_expansion/` | `formal_analysis.json` | `f6e4740cc7a1d25c7cd043879ccdce5f89704f8f37bda946dabcf40c897aa21e` |
| R417 | `results/research_loop/r417_energy_port_banks_k4/` | `formal_analysis.json` | `a96864f8a1d31548f1c1603462de43bde1c1c49bc561633d4c6ce74a765596da` |
| R419 | `results/research_loop/r419_slew_state_bundle/` | `formal_analysis.json` | `9aa5ddd24e7bbeaa992b02a14fde27c368c0f32688591a646adbf7146e86115e` |
| R420 | `results/research_loop/r420_objective_repair/` | `formal_analysis.json` | `f571966aba08f41612ec7ae217adb1e151a71f2bfdd70d92b7e3584a27b626b2` |
| R421 | `results/research_loop/r421_diagnostics/` | `formal_analysis.json` | `00dfc2e3ec4969dafc746241c8a6f1e8b994d8654f33cf1351df6750fd636a99` |
| R422 | `results/research_loop/r422_common_channel_repair/` | `formal_analysis.json` | `94791178d109eb282849150f3a9252e46694a45330d0807e5e3f72067ff595ff` |
| R423 | `results/research_loop/r423_value_estimation_repair/` | `formal_analysis.json` | `f7f19914c842ad85d5ccd0de77a49608fab8006a199f7a25177e34189a191534` |
| R424 | `results/research_loop/r424_guard_aligned_constraints/` | `formal_analysis.json` | `948c1864426867fe97bc2e6a70af2b9d0c168a690edba1fa742da94071df7f36` |
| R425 | `results/research_loop/r425_guard_constraints_signfix/` | `formal_analysis.json` | `080b6e2f6c7ffafe9f1bb95634773834458cadb9bcc1d53d50559e2b47e5831e` |
| R426 | `results/research_loop/r426_b2_five_seed/` | `formal_analysis.json` | `df9f7afae812fc04a1cb9595f5396e53541945fd4296e647d441bc8bb097a06d` |
| R427 | `results/research_loop/r427_critic_target_normalization/` | `formal_analysis.json` | `0c7bdf8394353e5bafe7a2259686045cbe5ac87f42dbf1819fedbe8495dd1ca6` |
| R428 | `results/research_loop/r428_c1_sac/` | `formal_analysis.json` | `9d20232faf44ded410bc7bd178cf2593dd8605dff4d01b1872e73e5fb22a97c0` |
| R430 | `results/research_loop/r430_adapted_sac_successor/` | `formal_analysis.json` | `b180c23840dc57d0ec2555126ba8ed0ba330d0f527d05e5d7c3f66c32216c602` |
| R431 | `results/research_loop/r431_sac_slew/` | `formal_analysis.json` | `a040191dc46d6daaf37923048128476b07f549a5a1482ca317f9aeabde097cdf` |
| R432 | `results/research_loop/r432_b3_diagnostics/` | `train/cd_matd3_message/seed401/diagnostics_summary.json` | `ab071bd66c86ae39b4dea1a96c47d1425fd271e733a0964bcc0fb31502f63918` |
| R433 | `results/research_loop/r433_sac_stress_penalty/` | `formal_analysis.json` | `b55f2edee6c20b0faf8926c417d93cd00e822f590f0151ba866dea0b58d188a2` |
| R434 | `results/research_loop/r434_sac_topology_variants/` | `formal_analysis.json` | `278f7ab038d13737de0c34c80e1cfa68d266bf380a778e86ff760e97581ec75f` |
| R435 | `results/research_loop/r435_multiplier_floor/` | `formal_analysis.json` | `e1e9db3c7bc181a95d91427a50723a13ed0631fbe311c7bfe41f4910dc37e50e` |
| R437 | `results/research_loop/r437_relaxed_spectral/` | `formal_analysis.json` | `10ae5d230449a2d1540b58225aaa282b1dff96f2b404ad1c79c71442d3f0e510` |
| R436 | `results/research_loop/r436_energy_residual_sac/` | `formal_analysis.json` | `82e9ab21836ecef50ad2dc11abc29256ac3ed89a981bf75fadb77d5a99a3ef31` |
| R439 | `results/research_loop/r439_timevarying_oracle/` | `formal_analysis.json` | `db7cd42422c5dbd30ef15d703eb4c31ad9f74a290f9ca7c42fbb4a1494cddfe5` |
| R438 | `results/research_loop/r438_sac_message_channels/` | `formal_analysis.json` | `0f16de4dcf67eb319a4d44f75610945e9afd51761d80297f3b2feee56c690c43` |
| R440 | `results/research_loop/r440_robustness_expansion/` | `formal_analysis.json` | `7cd23688fe9cb7f16c721d69728f92c7ba7456e41edbc9d2a19f6d9cfc226758` |
| R441 | `results/research_loop/r441_timevarying_guard/` | `formal_analysis.json` | `d9495b27d0de27b55456294cd65662daea4795d9e71ea36f79b0e8a5dd05af29` |
| R444 | `results/research_loop/r444_signed_probe_order/` | `formal_analysis.json` | `244998adb3ba421da7dd31ce47aa6912033262b181b77c2c0b577ed3bb5781ab` |
| R446 | `results/research_loop/r446_md_authority_fd/` | `formal_analysis.json` | `742a0816bbc0792222793e25aa56f921408772e6063d9f09ecd1eb3263a217f2` |
| R447 | `results/research_loop/r447_p1_complex_response/` | `formal_analysis.json` | `18b6a57e6b4616381b11abacb70c41a43e147ade635e05cc439458704d0a585be4` |
| R449 | `results/research_loop/r449_p1_sensitivity/` | `formal_analysis.json` | `621cae2c4cf527fea8fc848f23995ef0a8c4b616be56dbc98ebdd4522ed2fb7d` |
| R450 | `results/research_loop/r450_p2_delay_loop/` | `formal_analysis.json` | `39339ce2965767337e6a21ee013552339af396422cab729f485655776e4c10e8` |
| R453 | `results/research_loop/r453_m5_aggregate_repair/` | `formal_analysis.json` | `fa16eda8f71621a2bc37868c80b7349f30d107d8c627fe3020ea35178e41223d` |
| R454 | `results/research_loop/r454_m4_residual_local_audit/` | `formal_analysis.json` | `dacc138d16e4ce814b8de8a84f805b8b2612b821eb2d0385c06705a7154ac4c5` |
| R456 | `results/research_loop/r456_m1_dual_saturation/` | `formal_analysis.json` | `02bdaaaee8d561ff4e223d5d46f5277b589a39ce623ec3a429f9f19f36348e28` |
| R457 | `results/research_loop/r457_m2_head_causality/` | `formal_analysis.json` | `da6683e5e192a4343478115374357fa62489b2293f3422f964e8decdf0c4b324` |
| R458 | `results/research_loop/r458_dev_select_eval_validate/` | `formal_analysis.json` | `c48424301032b5c01f1216cbb8aa4c009cccf5e7892aa60c51b38aa63c602ca9` |
| R459 | `results/research_loop/r459_u1_u8_shared_export/` | `checks/verification_report.json` | `f27fac1b114a6495e49f92e9d8f1e832ec559b2b3610a690eef4e99ad571b5c7` |
| R460 | `results/research_loop/r460_u3_execution_semantics/` | `checks/verification_report.json` | `2a51f1377b75848f7fef9971c46f0d3bc2a42f10c4fa93bc73643c483a330d52` |
| R463 | `results/research_loop/r463_u4_guard_audit/` | `checks/verification_report.json` | `d557e47cdce6ccb03f8a87da0040bbff169d0a4290e85e68ef772c37221159f2` |
| R464 | `results/research_loop/r464_u1_qy10_certificate/` | `checks/verification_report.json` | `07f02a9160ffc167eb743b0c8ba8e9c3f5532a218f7915e16470ff6b9877050c` |
| R465 | `results/research_loop/r465_u5_total_sensitivity/` | `checks/verification_report.json` | `7b99bb7ebc344c762bfea68c5659eafd2e01f4d5e4904026ddfa149e9a4daa82` |
| R467 | `results/research_loop/r467_u6_fractional_delay/` | `checks/verification_report.json` | `af91e07f85b4b6f3d5a90a713ac1556f4f70bc425346bead5f3c537c3105bd19` |
| R468 | `results/research_loop/r468_u7_local_taylor/` | `checks/verification_report.json` | `564a2fa7c66c6f3a8b20fe01fe2f78854715582c11406c4591004679569c222b` |
| R469 | `results/research_loop/r469_u8_separation_bound/` | `checks/verification_report.json` | `57050677549689b7aaa9cd85b566bd6a71adadb23dc2f4825b53747612e2de1e` |
| R473 | `results/research_loop/r473_u2_source_factorial/` | `formal_analysis.json` | `b8786a5e9c3be3919ab4ca92e8b46747daaeb0e5405b4aa6b6e3d250bd333dda` |

The one hundred and eleven roots currently occupy 8,581,672,997 bytes. R286, R287, R291, R292,
R294, R295, R296, R297, R298, R299, and R300 raw traces remain ignored; their retained trace hashes are indexed by
each round's decision and provenance artifacts.

R466 is a preserved 99,253,032-byte engineering-invalid predecessor: its
complete linear export remains under `results/research_loop/r466_u6_fractional_delay/`,
but cyclic raw-telemetry serialization prevented a completed formal root. R467
is the create-only successor and does not pool R466's partial output.

R472 was owner-ordered shutdown with 96/108 valid training shards; its frozen
inventory is `tmp/yang_md_decoupling_marl/r472_shutdown_inventory_20260822.json`.
R473 is the create-only successor: the 96 complete shards enter via NTFS
hardlinks (816 entries, zero additional data bytes, all-same-inode verified),
the 12 missing `an_cn_r0`/`an_cn_r1` cells were trained fresh, and the full
evaluation/aggregate ran under the byte-identical R472 protocol.

R476 was aborted execution-incomplete: the pipeline exited after its first
training wave because the driver wrote its result under the scratch tree while
the pipeline searched the repository tree (driver fixed and regression-locked
in commit ef85ebf). The 16 complete wave-1 shards are preserved under
`results/research_loop/r476_u2_confirmatory/train/`; its frozen pipeline
inventory is `tmp/andes/r476_pipeline_inventories/`. R477 is the create-only
successor: those 16 shards enter by NTFS hardlinks after per-shard
scientific-identity verification (provenance:
`results/research_loop/r477_u2_confirmatory/r476_shard_import.json`), the
remaining 32 cells train fresh, and the full evaluation/aggregate runs under
the byte-identical R476 scientific protocol.

R366 `analysis.json` and `analysis_v2.json` are preserved pre-audit static
snapshots.  The first lacked one shared rowwise clip/slew seam; the second
overstated full-comparison identifiability before learning capacity, training,
tuning, seed/checkpoint, and sealed-evaluation budgets were frozen.
`analysis_v3.json` is the current decision artifact.

R371 `analysis.json` through `analysis_v4.json` are preserved pre-audit static
snapshots.  They respectively lacked actual-torque settlement, a current
torque-readback label, the bound governor-free V4 check, and fail-closed actor-
vector shape validation.  `analysis_v5.json` is the current decision artifact.

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
