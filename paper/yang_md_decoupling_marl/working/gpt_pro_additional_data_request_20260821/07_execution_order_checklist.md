# Codex 执行顺序与交付检查表

## 阶段 A — 先封存，不计算结论

- [ ] 阅读 delta brief、完整解答、R451 audit、R458 plan。
- [ ] 分配 successor round；确认历史结果只读。
- [ ] 生成 git/environment/RNG/command provenance。
- [ ] 建立 `object_registry`，严格区分 Object A/B。
- [ ] 封存 profile、scenario、reference、guard和units contracts。
- [ ] 生成所有输入 SHA-256 inventory。

## 阶段 B — 共享模型导出 WP1

- [ ] 导出 Object B 原始 DAE、input/output Jacobians。
- [ ] 导出 continuous reduced与pre/post-step sampled models。
- [ ] 导出 controller realizations、loop break与feedback sign。
- [ ] 导出 headroom/clamp active modes和unit scaling。
- [ ] 导出 Object A 八个M/D columns与execution hidden state。
- [ ] 独立验证 equilibrium、Schur reduction、ZOH和impulse response。

## 阶段 C — 先修/验 U3，再允许训练

- [ ] 生成 raw/prev/executed/physical command逐步trace。
- [ ] projector NumPy/Torch parity通过。
- [ ] replay与target action语义通过。
- [ ] toy MDP multi-step target通过。
- [ ] 查找R431 replay；不存在则记录不可精确重构。

## 阶段 D — U1/U4 certificate与guard

- [ ] 封存QY10 class contract和normalization。
- [ ] 验证gauge与baseline internal stability。
- [ ] 构造并验证DCF/Bézout；失败即停止，不硬继续。
- [ ] 生成90列response lift并finite-difference核验。
- [ ] 明确saturation路径。
- [ ] 解phase-I并导出unscaled primal/dual。
- [ ] 独立checker和高精度复核。
- [ ] 从raw trace独立重算全部guards。
- [ ] 对350 family或QY10运行exact finite-bank feasibility。

## 阶段 E — U5–U8

- [ ] U5：`rho±h,±h/2,±h/4` equilibrium/model/derivatives。
- [ ] U5：全频total derivative与Richardson/direct FD核验。
- [ ] U6：exact ZOH fractional-delay augmented model和pole branch tracking。
- [ ] U6：nonlinear `tau=0.1 s`，按二分规则继续。
- [ ] U7：mixed tensors/JVP、30-step lift、amplitude sweep、mode trace。
- [ ] U7：additive port lift和singular values。
- [ ] U8：I/O Toeplitz cross lift、conditioning和bound。
- [ ] U8：仅在full-state projector通过物理/代数验证后计算commutator。

## 阶段 F — R458

- [ ] 验证R458 source/seal/candidate hashes。
- [ ] capacity/rehearse/prepare通过。
- [ ] 运行dev shards。
- [ ] select仅读取dev inventory。
- [ ] 封存selection hash后才运行eval。
- [ ] eval只运行同一winner。
- [ ] aggregate/classify并独立重算branch×K。
- [ ] 不重试、不改threshold、不重选。

## 阶段 G — U2 factorial（最后）

- [ ] 先完成power/materiality/preregistration。
- [ ] 生成独立donor bank和placebo audit。
- [ ] 18 cells同维、同初始化、同预算、reward正交。
- [ ] 所有RNG在网络构造前设置。
- [ ] training seed为顶层单位。
- [ ] 运行held-out eval并保存profile-level raw outcomes。
- [ ] paired contrasts和budget sensitivity完成。
- [ ] 不足power或未收敛时标探索性/未识别。

## 阶段 H — 独立核验与打包

- [ ] 独立脚本重算模型、endpoint、guards、certificate和selection。
- [ ] 所有 checks 写入 `verification_report.json`。
- [ ] claim-evidence map覆盖每个决策性数字。
- [ ] 根 `SHA256SUMS` 全通过。
- [ ] 压缩包解压后再次全量验哈希。
- [ ] 最终报告逐 U 标明 `supported/refuted/unresolved/invalid`。
- [ ] 未产生的数据使用 `null + reason`，不写占位数值。
