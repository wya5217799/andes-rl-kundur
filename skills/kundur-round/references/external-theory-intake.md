# External theory intake — 外部数学/理论解答的吸收契约

外部数学/理论解答 (GPT Pro / theory-audit bundle / 外部 solver / 外部咨询文档
等) 是**设计辅助，不是权威**。它们进项目时先三分，每类走不同吸收路径。
本文件是三分定义与可执行细节的唯一契约；`CLAUDE.md` 只持触发指针 + 强制
lint 调用。
动机 (R422/R424/R432): 机制结论曾只吸收一半——代数恒等式进了论文，机制
预测要求的可观测量无人登记、无人测，事后补算翻车三次。契约把"理论要求
翻译成实验登记项"变成强制步骤。

## 出 brief (提问材料)

外部 LLM 没有仓库访问，brief 必须**自包含**——不能留 pointer
(writing-for-agents 的"指针优先"默认读者有仓库，此处不适用)。每条定义
(reward 公式、cost 定义、dual update、模态矩阵、参照统计) 都要内联数值，
不能写"见 feed"。缺定义 → 外部 LLM 答不了对应问题，只能泛泛而谈。

- 提问按三分标注类型 (A 代数 / M 机制 / P 论文级)。
- 机制问题要求对方给可证伪方向 + 可观测清单 (喂给本契约的 Theory intake)。
- 数据打包: 结论承载 JSON + 摘要文本；排除大 raw trace (如逐步 CSV)，README
  说明出处与校验方式。

## 三分定义

| 类 | 判据 | 吸收路径 |
|---|---|---|
| **代数恒等式/定义层** | 由冻结公式直接推出，不依赖训练结果 (Parseval 分解、cost 结构恒等式、KKT 结构) | repo-side 数值验证 → 进 feed/手稿 |
| **机制预测/可证伪假设** | 依赖训练/实验结果的因果或方向断言 ("把 effort 放 common 会 X"、"训练买不到 guard") | 可观测清单 → seal 或 not-pursued → 裁决写回 |
| **论文级数学命题** | 可作为定理/引理/推导进论文的数学结论 | 四证齐 → 手稿 theory 段；否则设计辅助 |

## 代数恒等式/定义层

- 必须 repo-side 数值验证：写一个 `probes/` 探针，在 sealed 轨迹或冻结公式
  上重算该恒等式，残差门槛 (R423 先例: ≤1e-18 量级，取决于量纲)。
- 验证通过才可进 feed/手稿；验证失败 = 恒等式不成立或引用错，禁止进入。
- 探针是 execution amendment 或 plan-registered probe，不是离线手算。

## 机制预测/可证伪假设

每条机制预测必须产出**可观测清单**——无论假设来自外部解答还是内部诊断
推导 (R435 教训)。清单是 plan 里的 `## Theory intake` 段
(或等价机器字段)，每行一个量：

```
observable: <名称>
  definition: <精确定义，含单位/归一化/聚合窗口>
  source: <从哪个日志/checkpoint/trace/JSON 读，path:locator>
  predicts: <该量如何裁决对应的机制预测 — 支持/否定的符号或阈值>
```

清单二选一落地：

1. **进 seal**：进入下一轮 sealed 协议的 frozen observables，rehearsal 验证
   "这个量真的可读" (同 objective_semantics_lint 的 rehearsal 验证地位)。
2. **not-pursued**：本轮 plan 登记 `not-pursued: <理由>` (数据不存在 / 成本
   超预算 / 超出本轮 scope)。理由必须具体，不能写"没必要"。

清单在 seal 前登记。事后发现缺量 = 本契约违约，记 gate calibration。

裁决写回：feed 的 Follow-up pointers 或 Conclusions 必须显式给出每条预测的
`supported` / `refuted` / `undecidable`，不得静默丢弃。undecidable 必须说明
为什么 (缺哪个量 / 哪个条件未满足)。

## 论文级数学命题

可进论文的定理/引理/推导，晋升前必须**四证齐**：

1. **自包含证明**：不是断言，是可复现的推导 (符号或逐行)。
2. **repo-side 验证**：符号验证 (sympy) 或数值验证 (探针残差)。
3. **假设边界明确**：理想模型 vs 真实 DAE 的每条假设写明 (对称/线性/均匀
   M,D 等)。
4. **model-theory gap 标注**：与真实 ANDES DAE 的差距写明 (如真实 DAE 输入
   Jacobian `B_{u,r}=f_u-f_y g_y^{-1} g_u` 未识别，见
   `manuscript_evidence_map.md` Model-theory gap)。

四证齐 → 登记进手稿 theory 段 (Proposition/Lemma)，成为论文资产。
任一证缺 → 只做设计辅助，不进论文正文，但可进 Discussion 的 future work。
历史判例 (哪些已过/不过) 见 `working/theory_audit_bundle/IMPORT_NOTE.md`
与 `working/manuscript_evidence_map.md` 的 "Assessment of the supplied
mathematical files"。

## 强制门禁

evidence round 收尾前跑
`python memory/tools/external_theory_intake_lint.py R<N>` (与
`objective_semantics_lint.py` 同级)，exit 1 = BLOCK。判定分支 (OK / HINT /
VIOLATION / PENDING) 与检测关键词住 lint 工具 docstring/源码，此处不复制。

## 回答吸收收尾清单 (外部解答回来后)

不靠 repo_health 报错兜底，按清单主动走 (2026-08-19 教训):

1. 独立验证每个数字 (不轻信): 代数结论 pwsh/python 重算；机制预测查是否被
   独立实验证实/否定。
2. 修正解答发现的数据错误 (sealed feed 走 execution amendment + publication
   gate 记录)。
3. 登记: 主报告登记进 ARTIFACTS.json (external-question)；配套文件 (复算
   脚本/派生 JSON/校验) 移 `tmp/<line>/`，不留在 working/ 造成
   DOCUMENT_UNREGISTERED。
4. 刷新 line-state 的 input_hashes (改了 feed 就触发)。
5. 修解答暴露的规则漏洞 (如 lint 触发范围)，同步 CLAUDE.md/reference/tests。
6. 写 gate calibration 一行。
7. 验证: lint 测试 + feed_check + validate + repo_health 全绿。
