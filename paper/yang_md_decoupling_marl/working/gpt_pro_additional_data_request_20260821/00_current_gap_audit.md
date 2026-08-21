# 当前包的已核对缺口

本请求依据以下已存在事实整理：

- R405 `linearization_matrices.json` 只有每 profile 的 `f_x(102×102),f_y(102×284),g_x(284×102),g_y(284×284),x0,y0,baseline_m0,baseline_d0`；没有 Object B control/disturbance columns和output map。
- R447 正式分析只保留 `n=102,m=4,r=3,p=4`、两种闭环维数、spectral-radius summaries和频带能量；runner内部实际构造了 `sampled_model.state_matrix/input_matrix/output_matrix`，但没有导出。
- R450 只导出 0.3–0.5 Hz 的41个 `L0` matrices、整数delay endpoint和局部最小 return-difference singular value；没有 full Nyquist loop、continuous/ZOH split或pole branches。
- R446 已证明八个 M/D reduced first-order columns为0，但没有 mixed second derivatives `N/E/R/S`。
- R451 明确为 `CANARY-INVALID`：placebo无效、seed晚于网络构造、raw/executed mismatch、reward/access混杂；不能修补旧outcomes。
- R431 formal manifest列出 checkpoints，但当前上传包不含原始 replay buffers；因此历史 Bellman bias是否可精确定量取决于主仓库是否仍保留 replay。
- R452/R453 给 finite 350 schedule family 的 summary/guard结果；要审计真实性仍需原始轨迹或可重复执行。
- R458 在输入包时只有 plan/runner/tests，无正式 outcome。
- 现有包有完整 SHA256SUMS，但 manifest没有足以恢复运行现场的git commit/dirty patch、完整环境锁和命令流水。

因此 Codex 的第一任务应是“导出和封存已有运行时实际构造过、但 formal summary 未保存的原始矩阵/轨迹”，而不是先增加更多文字推导。
