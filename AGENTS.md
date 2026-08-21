# Codex research bootstrap

完整工程规则在 `CLAUDE.md`——文件名是历史遗留, 与 Claude Code 工具无关;
它是本仓库工程规则唯一真源。改代码或仓库治理前必读。

本仓库是 TPWRS 导向的自动研究项目, 不是开放式算法扫荡。

## Session start

1. 点名手稿: `python memory/tools/session_context.py --json --line <id>`
   (id 未知先 `--list-lines`)。未点名: `python memory/tools/session_context.py --json`。
2. 只读它返回的 bounded `required_reading`; 不批量加载历史 ledger, 除非当前任务需要。
3. 按它报告的 mode 走完整仪式 (resume-round / research / manuscript /
   manuscript-refresh / idle): `skills/kundur-round/SKILL.md` §1。
4. 领 round 前按 `skills/kundur-round/SKILL.md` §2 classify the work as `scratch`, `manuscript`, or `evidence`; evidence 先领号再执行, id 只经原子工具 (CLAUDE.md Tools)。
5. 收尾顺序、feed 契约、`## 给 PI 的话` 交付契约 (From R317 onward 只答
   三段人话, ADR-0011): `skills/kundur-round/SKILL.md` §2-3 + CLAUDE.md。

## Repository learning

Repository tutoring is explicit-only. Enter `atomic-stem-tutor` Repository
mode only when the user explicitly invokes `$atomic-stem-tutor`; ordinary requests to
understand, explain, or interpret the repository receive a direct answer.
`learning/` 切片只在 `$enrich-project-learning` 时持久化, 注册契约见
`learning/README.md`; `learning/` 非权威, 永不替代 source/feed/claim/verdict。
完整契约: `docs/repo-hygiene/external-skills.md`。

