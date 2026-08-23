# Ledger writing — claim / question / note 写法 (从 CLAUDE.md 下放, 2026-08-23)

四 schema 实体 + handoff 草稿。STATE.md 只读 claims/questions/rounds; handoff 不进 oracle。

## claim (CLM-NNNN)

- 时机: 新数字结果 (`finding`, trust V/S/T); 纠正旧数字 (`correction`, trust V + supersedes); 研究方向转向 (`decision`, trust S).
- 形态: **注册卡** — 一段自包含 statement (分类判定 + 主头条数字对 + 范围短语) + provenance 指向 feed/results.
- R281+ verified finding/correction 另带结构化 `evidence_refs`: repo-relative JSON `path`、RFC 6901 `locator`、whole-file `sha256`、`role`. 每级表格 / 位置子表 / 守卫明细只住 results 与 feed, 不复制进 claim — 第三份拷贝是 fork (单一真源分配表见 `kundur-round` SKILL.md §3).
- R291+ statement 硬上限 1800 UTF-8 bytes; 超出 = 注册卡在复制 feed, 应缩回分类 + 一个头条结果 + 范围.

## question (Q-NNNN)

- 时机: verdict 记下但本轮没回答的 follow-up.
- statuses: open / in-flight / closed-*. closed 必须有 closed_round (存在目录) + closed_by (存在 claim).

## note (NOTE-NNNN)

- 时机: 外部存档文件 (handoff/ADR/eng-note/legacy doc) 值得索引: `new_note.py --source ... --topic ...` 然后填 stub.
- Note 只持摘要、claim candidates 与相关指针, 不持 active task; 未决工作必须升级为 Q-NNNN 或写入当前手稿 `LINE.md`.
- 仓库内部 `docs/adr/` 已是 canonical, 不再要求另建 Note 索引.

## 归档判据

按未来决策价值, 永不按字数·年龄. 判据: 这条 rationale 还会约束未来改动吗? keep = 负保证 / 持久边界 / 复现条件 / 安全规则 / 重新引入条件; archive = 一次性 UI / 已闭合 minor bug / 被取代实现细节 / 当前行为别处显然. 字数与年龄只是发现线索, 不是归档判据.
