# R485 generated-only solution bundle

本包只包含本轮生成的数学结论、验证脚本、实际运行输出和交付清单；不包含用户上传 ZIP、解压后的原始 JSON、源码副本或其他输入数据。

## 先读

- `SOLUTION.md`：完整结论、证明、反例、条件定理、论文措辞与 obligation closure。
- `DERIVED_RESULTS.json`：实际 checker 生成的机器可读派生结果。
- `verification.py`：标准库验证脚本；从原始输入 ZIP 就地读取，不复制数据。
- `verification-output.txt`：脚本实际 stdout。
- `verification-stderr.txt`：脚本实际 stderr；本次为空文件。
- `VERIFICATION_RECORD.md`：命令、环境、hash、exit status 和证据范围。
- `DELIVERY_MANIFEST.json`：本 ZIP 的 allowlist、成员大小/SHA256 与排除项；清单自身因自引用只记录大小，不记录自身 SHA256。

## 核心裁决

- frozen metric arithmetic：有效且远离阈值；
- metric classification：`construct-limited command-activity metric`；
- physical no-harm implication：`refuted_by_counterexample`；
- actual hardware harm/safety：`information_insufficient`；
- physical-stress proxy：仅在显式新增假设下 `conditional`；
- `VALID-MIXED`, `121/208`, `0/208`：保持不变。

## 复现

将原始 `r485_gpt_pro_action_guard_20260831.zip` 放在任意路径后执行：

```bash
python verification.py \
  --input-zip /path/to/r485_gpt_pro_action_guard_20260831.zip \
  --json-out DERIVED_RESULTS.reproduced.json
```

脚本不联网、不仿真、不训练、不修改输入。
