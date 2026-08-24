# Research-agent bootstrap

科研与工程规则在 `CLAUDE.md`——文件名是历史遗留, 与具体 agent
或工具无关; 它是科研工程规则唯一真源。日常交互、执行 lane 与长任务授权
以本文件为准。运行时若已注入 `CLAUDE.md` 全文则算已读,
否则改代码或仓库治理前只读一次。

本仓库是 TPWRS 导向的自动研究项目, 不是开放式算法扫荡。

## 默认交互契约

- **SHORT-FIRST**: 默认把请求当短任务处理: 精确读取、定向检查、尽快给
  第一条有用反馈。代码改动不自动授权 build、全量测试、ANDES、训练、
  eval、扫参、后台 worker 或正式 evidence 执行。
- **LONG-AUTH**: 只有 owner 在当前消息明确说「长任务」, 或明确要求启动
  某个已点名的长动作, 才进入长任务。预计任一命令或总执行 >60s,
  或命中上述长动作但未获授权时, 只报告目的、预计时间、产物和停止条件;
  「继续」「看看」「审查」「修复」「优化」本身只授权相应短任务。
- **OWNER-PLAIN**: 对 owner 用完整自然中文, 结论先行, 说明发生了什么、
  这意味着什么、下一步是什么。专业词首次出现时解释作用; 编号、文件名和
  内部流程只在影响决策、用户要求或需要追溯时给出。

## Session start

0. 先选最小执行 lane; 默认 FAST, 到达该 lane 完成条件即停止:
   - **FAST**: 固定范围只读/`scratch`; 用已注入规则, 只查精确目标,
     直接答复。只有当当前 line/round 决定答案时跑 `session_context`。
   - **STANDARD**: scoped code/governance `scratch`; `session_context` 一次,
     精确文件 + focused tests, 用固定 diff 收尾。
   - **FORMAL**: round/evidence/manuscript、ANDES 执行或正式审查;
     还必须满足 LONG-AUTH 才能启动长执行; 完整执行以下 gate。
1. 仅 STANDARD/FORMAL 跑上下文恢复。点名手稿:
   `python memory/tools/session_context.py --json --line <id>`
   (id 未知先 `--list-lines`)。未点名: `python memory/tools/session_context.py --json`。
2. 只读它返回的 bounded `required_reading`; 不批量加载历史 ledger, 除非当前任务需要。
3. 仅 FORMAL 按它报告的 mode 走完整仪式 (resume-round / research / manuscript /
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
- **launch parallel first** (2026-08-25 R478 repair5): 启动高并行仿真前,
  先查历史容量证据 (memory/rounds/*/capacity*.json 的 selected_workers;
  R452-R477 全为 16 并行先例, 同主机同负载)。有完整阶梯证据 + owner
  时间紧急指令 → 复用历史选择, 只跑单档 16×8 快速确认, 不重爬完整
  6 档阶梯。授权哈希文件必须在所有 plan/source 修改提交后再生成
  (repair4 因改 plan 导致哈希绑定漂移的教训)。
- **PI 交付**: `## 给 PI 的话` 仍按 kundur-round 的更严格三段契约。
