# 无泄漏写作 + 精简保命题 (feed/claim/verdict/plan)

`kundur-round` §3 已定单一真源 + "写陈述不写叙述"。本文件补两类规则:
(1) 思维链/设计会话泄漏的判定与处置; (2) 在 claim 1800B / verdict 80 行 /
feed 两页的 cap 下精简时怎么保命题。吸收自 deepseek-harness 的
`dsh-trim-cot-leakage` + `dsh-prose-standard`, 已适配本仓库 ledger 词汇。
probe 工具: `memory/tools/cot_leakage_lint.py`。

## 一个测试

一段话的视角应是仓库, 不是写它的那个会话。判据: **一个在 HEAD、看不到任何
会话记录 / 评审串 / 未提交草稿的读者, 能不能解析每个引用、验证每个断言?**
不能 → 泄漏。可解析只是过了这条线; 当前态面上可解析的变更故事仍是叙述。

## 泄漏分类 (删 / 重述)

1. 死设计会话引用 — `(decision 7)`、`(audit C2)`、`design §4.7`、阶段标签。
   有 committed owner (claim / round 目录 / ADR / issue) 就按名+路径引用; 否则
   删引用, 把事实从句重述为独立成立。
2. 轮次视角叙述 — "本轮加X"、"上一轮是Y"、"this PR adds"、"a later round"。
   改陈述当前机制/扩展点; deferred 升 `TODO` 或 `Q-NNNN`。
3. 变更叙述与版本戳 — "used to / no longer / 旧X / v1 / 今天 / 现在" 与过去
   对比。改陈述现在行为; 修好的回归写现在时反事实 ("without X, Y happens"),
   不写仓库史。
4. 评审编排 — "rejected in review"、"reviewer 确认"、草稿序号 ("v5 of this")。
   留结论与理由作普通事实, 删"谁在何时说"。
5. 面向评审的自证 — "this is correct because…"、"the cast is safe — it just…"。
   写使代码安全的不变式, 或删 (代码已展示)。
6. 重述与推导转录 — 控制流叙述 ("first we X then Y")、测试走查、显然分支证明。
   删; 只留非显然契约/不变式。
7. hedge 与计划残留 — "probably fine"、"should be enough"、无 marker deferral。
   升 `TODO`/`FIXME` 或重述为实际界; 删 hedge。
8. 作者语言串味 — 英文 prose 夹中文工作语言片段, 或中文面夹英文。翻译或删。
   (给 PI 的话整体中文 / plan·verdict 技术骨架中文是 policy, 不是串味。)

## 非泄漏 (keep)

- claim id (`CLM-NNNN`)、round 目录 (`R<N>`)、`evidence_refs` locator — HEAD 可解析。
- issue 引用、`TODO(name)`、suppression justification (disable/ignore 理由)。
- 现在时反事实回归钉 ("without X, Y happens")。
- measured bounds ("measured: 512 nests ≈ 0.15s")。
- 外部引用 (RFC §、Figma frame 名)。
- "we" 作项目语态。
- sealed 历史快照与 recorded 输出保持原声, 不回填改写。

## 精简保命题

cap (claim 1800B / verdict 80 行 / feed 两页) 是"移走", 不是"删事实"。精简前先
枚举命题, 每条保留: actor + action; condition / timing / ordering; modality
(must / may / never); 负保证 + 例外; ownership / side effect / failure mode /
consequence。删形容词/重复/叙述只在每条事实从句存活且结果更清晰时。更短 ≠
更好。

## 工作流 (步骤)

1. scope 显式; 先只读审计, 不猜全仓 scope。跳过 `vendor/`、archived/、recorded
   快照与 sealed 历史。
2. 跑 `python memory/tools/cot_leakage_lint.py R<N>` 当 recall battery; 它是
   probe, 会漏, 还要读最密的 prose (feed observations / claim statement /
   verdict TL;DR) 手判。
3. 删前枚举命题, 查 overcorrection: 义务→认可、假设→已发布特性、删真事实、
   丢 provenance。
4. verify: 每个保留引用 HEAD 可解析; 重跑 battery 只剩 sanctioned keeps。

## 适用面

feed、claim 卡、verdict 技术骨架、plan、docs。不适用: 给 PI 的话 (自有更严
规则)、results JSON、sealed 历史。

完成判据: 泄漏分类 1-8 无未处置命中; 每处删减命题存活; 保留引用 HEAD 可解析。
