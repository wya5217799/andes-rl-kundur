# VSG Failure Mathematics Advisory — Markdown-First Bundle

本压缩包是 `gpt_pro_math_pack_20260820.zip` 的 **Markdown 优先版数学顾问交付**。核心报告、P1/P2/P3 相机就绪数学、论文英文段落、中文摘要、限制清单、结论强度矩阵和九个问题的独立答案均为 `.md` 文件；未放入 DOCX 或 HTML 成品，避免打开压缩包后只看到 Word 文档。

## 直接阅读

1. [`01_FULL_MATHEMATICAL_ADVISORY.md`](01_FULL_MATHEMATICAL_ADVISORY.md) — 完整英文数学顾问报告。
2. [`02_P1_P3_CAMERA_READY_MATHEMATICS.md`](02_P1_P3_CAMERA_READY_MATHEMATICS.md) — P1/P2/P3 优先问题的假设、命题、证明与验证方案。
3. [`03_PAPER_READY_PARAGRAPHS_P1_P3.md`](03_PAPER_READY_PARAGRAPHS_P1_P3.md) — 三段有界强度的 publication English。
4. [`04_EXECUTIVE_SUMMARY_CN.md`](04_EXECUTIVE_SUMMARY_CN.md) — 中文执行摘要。
5. [`05_ONE_PAGE_SUMMARY.md`](05_ONE_PAGE_SUMMARY.md) — 九题一页汇总表。
6. [`problems/00_INDEX.md`](problems/00_INDEX.md) — 九个问题的独立详细文件，顺序为 P1、P2、P3、M3、M5、M4、M1、M2、C1。

## 证据与复核

- `evidence/evidence_register.md`：225 条证据的可读 Markdown 账本。
- `evidence/evidence_register.csv` 与 `.json`：机器可读原始账本。
- `evidence/json_pointer_catalog.tsv.gz`：封存 JSON 的完整叶字段目录。
- `verification/m_observable_matrix.md`：M 类问题的机械可检查 support/refute 矩阵。
- `verification/`：P1 复灵敏度、P2 延迟边界、P3 DAE 有限差分、C1 精确锥对偶检查等脚本。
- `source_package/gpt_pro_math_pack_20260820.zip`：原始封存证据包的精确副本。

## 一键核验

在包根目录执行：

```bash
./verification/run_with_bundled_source.sh
```

该流程核验源文件哈希、直接 JSON 字段、派生证据重建、C1 的 HYPOTHETICAL 烟雾测试和数值追溯 lint。数学假设不是实验事实；M 类条目仍是可证伪机制预测，P 类条目仍受各自假设和验证计划约束。

完整目录见 [`00_CONTENTS.md`](00_CONTENTS.md)，全部 Markdown 文件清单见 [`manifest/MARKDOWN_FILES.md`](manifest/MARKDOWN_FILES.md)。
