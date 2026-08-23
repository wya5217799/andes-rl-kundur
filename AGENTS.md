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

## 会话工作纪律 (2026-08-23 Codex 复盘)

多任务/审查/复盘会话的协作纪律, 对一切 agent 生效, 每条来自一次真实返工:

- **task queue**: 同一会话接多个大任务时, 开工前列显式队列, 每条回复末尾
  复述队列; 被新指令打断后, 处理完必须回到未完成项 (教训: 优化任务被
  审查任务淹没, 永久丢失)。
- **freeze-then-review**: 双审只审冻结提交 (`reviewed_commit` + 文件哈希);
  先修完全部 P0/P1 再派审; 修完重审只审新冻结提交, 不审中间工作区
  (教训: 审中间状态 → 修 → 再审, 两轮往返)。
- **once-then-grep**: 冷启动读 CLAUDE.md + session_context 输出后即开工;
  同一会话不整篇重读规章, 需要时 grep 定位; 子代理只拿任务简报与文件路径
  (教训: 主会话与两个审查子代理各重读规章五遍以上)。
- **long-run background**: 预计 >5min 的命令后台跑; 启动仿真前先查同名进程
  是否已在跑, 不重复启动; 不轮询, 等完成通知。
- **说人话**: 对 owner 用完整自然中文, 一次一个问题, 正文不出现仓库编号/
  文件名/术语 — 本仓库最高频 owner 纠正, 外部 agent 同样遵守。

