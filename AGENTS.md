# Research-agent bootstrap

完整工程规则在 `CLAUDE.md`——文件名是历史遗留, 与具体 agent
或工具无关; 它是工程规则唯一真源。运行时若已注入其全文则算已读,
否则改代码或仓库治理前只读一次。

本仓库是 TPWRS 导向的自动研究项目, 不是开放式算法扫荡。

## Session start

0. 先选最小执行 lane:
   - **FAST**: 固定范围只读/`scratch`; 用已注入规则, 只查精确目标,
     直接答复。只有当当前 line/round 决定答案时跑 `session_context`。
   - **STANDARD**: scoped code/governance `scratch`; `session_context` 一次,
     精确文件 + focused tests, 用固定 diff 收尾。
   - **FORMAL**: round/evidence/manuscript、ANDES 执行或正式审查;
     完整执行以下步骤与对应 gate。
1. 点名手稿: `python memory/tools/session_context.py --json --line <id>`
   (id 未知先 `--list-lines`)。未点名: `python memory/tools/session_context.py --json`。
2. 只读它返回的 bounded `required_reading`; 不批量加载历史 ledger, 除非当前任务需要。
3. 按它报告的 mode 走完整仪式 (resume-round / research / manuscript /
   manuscript-refresh / idle): `skills/kundur-round/SKILL.md` §1。
4. 领 round 前按 `skills/kundur-round/SKILL.md` §2 classify the work as `scratch`, `manuscript`, or `evidence`; evidence 先领号再执行, id 只经原子工具 (CLAUDE.md Tools)。
5. 收尾顺序、feed 契约、`## 给 PI 的话` 交付契约 (From R317 onward 只答
   三段人话, ADR-0011): `skills/kundur-round/SKILL.md` §2-3 + CLAUDE.md。

## Runtime compatibility

在 Codex 以外的 agent、Windows、工具 schema/编辑拒绝后、或启动预计
超过 5 分钟的任务前, 读 `docs/agents/runtime-compatibility.md`; 该文档只适配执行能力,
不改变 round、seal、evidence 或手稿 authority。

## Repository learning

Repository tutoring is explicit-only. Enter `atomic-stem-tutor` Repository
mode only when the user explicitly invokes `$atomic-stem-tutor`; ordinary requests to
understand, explain, or interpret the repository receive a direct answer.
`learning/` 切片只在 `$enrich-project-learning` 时持久化, 注册契约见
`learning/README.md`; `learning/` 非权威, 永不替代 source/feed/claim/verdict。
完整契约: `docs/repo-hygiene/external-skills.md`。

## 会话工作纪律 (2026-08-23 多运行时复盘)

多任务/审查/复盘会话的协作纪律, 对一切 agent 生效, 每条来自一次真实返工:

- **task queue**: 同一会话接多个大任务时, 用运行时 plan/todo 维护队列;
  无此能力才在对话里列简表。只在状态变化、被打断或有未完成项时复述;
  处理插入任务后只回到仍未完成的明示任务队列。
- **freeze-then-review**: 正式双审只审冻结提交 (`reviewed_commit` + 文件哈希);
  先修完全部 P0/P1 再派审, 重审只审新冻结点。scratch 自查只需固定 diff,
  不为制造审查点强制提交用户的脏工作区。
- **once-then-grep**: 已注入的 CLAUDE.md 算已读; 否则冷启动读一次。读完
  session_context 的 bounded 输出后即开工;
  同一会话不整篇重读规章, 需要时 grep 定位; 子代理只拿任务简报与文件路径
  (教训: 主会话与两个审查子代理各重读规章五遍以上)。
- **long-run background**: 预计 >5min 的命令后台跑; 启动仿真前先查同名进程
  是否已在跑, 不重复启动; 不轮询, 等完成通知。
- **说人话**: 对 owner 用完整自然中文, 一次一个问题;
  保留学科通用专业词并在首次出现时说明它在本句的作用。仓库编号/文件名
  只在用户要求核对、影响决策或需要可追溯时出现;
  `## 给 PI 的话` 仍按 kundur-round 的更严格三段契约。
