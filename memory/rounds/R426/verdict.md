# R426 verdict — B2 五种子扩展:位复现门通过、冻结三种子判定逐块复现旧结论、五种子中位负对比保持(-74.98%/-35.49%),离散度首次披露

**Date**: 2026-08-18
**Status**: completed
**Type**: experiment
**Wall**: ~3.5h（训练 7 组并发 ~2.5h + 评估/分类 ~1h）

## TL;DR

R426 extends the R410-repaired bundle (the paper's headline negative message contrast) from three to five seeds per arm under the pre-registered bit-repro gate: the fresh message|401 gate run reproduces the stored R410 checkpoint byte-for-byte (BIT-REPRO-CONFIRMED, DRIFT not entered) and the frozen three-seed tree over the reused checkpoints reproduces the sealed R410 verdict and guard profile exactly (CANARY-FAIL, 34/36/24/28/35). The five-seed-median message improvement over the matched no-message arm is -74.98% off-diagonal / -35.49% differential versus the three-seed -78.43% / -26.74%, so the negative contrast survives the seed-count extension, while the five-seed table discloses the dispersion the three-seed median hid (no-message off-diagonal spread 3.81x versus 1.84x message, 1.77x scalar).

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R426.md`

## 给 PI 的话

**发生了什么**：把论文头条对比所在的实验组，从每个控制器三个随机起点扩到五个，并按要求先做了一次"复制门"验证：用当前代码重跑其中一个组，得到的学习结果和先前保存的结果逐字节一致，因此旧数据可以直接复用，只补训了六个新组。全部七组训练完整有效，对照控制器逐字节一致。冻结的旧判定在这批数据上把之前的失败结论逐块复现了出来。

**这说明什么**：论文那条"通信没有带来正面增益"的头条对比经受住了起点扩充的考验——五个起点的中位结论和三个起点的方向一致，一条指标上负面程度还更深。这说明旧结论不是三个起点碰巧造成的。同时五起点第一次暴露了隐藏的波动：对照组里有一个起点的表现明显差于其余四个，说明结论稳定在"中位"层面，逐个起点看并不一致，论文里应当如实披露这个波动。

**下一步做什么**：默认动作不变：修估价网络的目标值尺度，这是清单上的下一项，也是两轮修正后仍然存在的直接病灶。论文侧按既定节奏更新这一节的结果表，把五起点的中位数、最差最好值和波动写进去。真正意义上的"新场景复验"仍然没做，如果需要更强的推广性证据，下一步可以在全新场景组上跑同样的控制器，但这会显著增加计算量，需要您定夺。
