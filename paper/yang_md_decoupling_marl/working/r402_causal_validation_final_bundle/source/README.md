# R402 causal-validation 审计交付包

本目录是对 `r402_causal_validation_v1.zip` 的独立复算、源码审计和后继实验设计。核心结论见：

- `R402_causal_validation_final_report.md`：完整中文审计报告与 manuscript-ready English；
- `CODEX_ANDES_execution_runbook.md`：可直接交给 Codex 的 ANDES 后继执行规范；
- `data/audit_summary.json`：机器可读摘要；
- `data/implementation_findings.csv`：实现缺陷与证据边界；
- `data/hypothesis_verdicts.csv`：候选机制的 epistemic status；
- `data/required_next_experiments.csv`：E0–E8 最小实验矩阵；
- `reference_fixes/`：两个可应用补丁、slew-aware reference interface、componentwise effort code 与 prospective contract；
- `code/r402_validation_audit.py`：从上传包独立复算全部派生数据；
- `tests/`：审计与 reference code 的自动测试。

## 已确认

- 40 个评估 JSON、240 条轨迹，计数为 216 learning + 24 deterministic；
- 两项 endpoint 与冻结表的最大绝对复算误差小于 `2e-18`；
- 全部 36 个 learning arm–seed–profile blocks 同时失败 common 和 action-stress guard families；
- no-message actor 在 behavior/evaluation 被 mask，但 actor/target update 使用未 mask replay observation；
- 三个学习臂的 executed action 经过 stateful slew，而 learner state/actor-target optimization 未建模该 projector state；
- 包内未执行 M0–M7、S0–S5 或 R402-specific DAE authority export，因此具体 root-cause effect 仍须 prospective paired intervention。

## 环境

```bash
python -m pip install -r code/requirements.txt
```

## 重新生成数据

先解压用户提供的 `r402_causal_validation_v1.zip`，然后运行：

```bash
python code/r402_validation_audit.py \
  --package-root /path/to/r402_causal_validation_v1 \
  --output-dir ./generated \
  --source-zip /path/to/r402_causal_validation_v1.zip
```

预期输出：32 个 CSV/JSON 文件，终端显示：

```text
records=240, profile_blocks=40, endpoint_rows=10
```

## 运行测试

```bash
R402_PACKAGE_ROOT=/path/to/r402_causal_validation_v1 pytest -q
```

当前交付验证结果：`9 passed`。

## 应用 reference patches

在完整仓库、审计绑定 commit 上：

```bash
patch -p1 < reference_fixes/0001_fix_no_message_actor_training_mask.patch
patch -p1 < reference_fixes/0002_apply_frequency_adapter_consistently.patch
```

两个 patch 已在复制源码基线上依次进行 dry-run/application 与 Python compile 检查。它们是后继实验的参考修复，不会追溯改变历史 R402 结果。

## 数据解释层级

- `registered_*`：从 raw evaluation JSON 独立复算的注册量；
- `action_*`、`checkpoint_*`、`retained_tail_*`：post-hoc diagnostics；
- `implementation_findings.csv`：可由源码直接推出的 code-mechanical facts；
- `hypothesis_verdicts.csv`、`root_cause_ranking.csv`：证据分类和判别优先级，不是 causal effect estimates；
- `required_next_experiments.csv`：真正识别贡献所需的 prospective interventions。

## 完整性

`SHA256SUMS` 覆盖交付目录中除其自身外的全部文件；压缩包 hash 在最终回复和同名 `.sha256` 文件中提供。
