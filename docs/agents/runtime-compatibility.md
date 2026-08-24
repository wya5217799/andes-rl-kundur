# Agent runtime compatibility

本文只适配 Codex、DeepSeek Harness 与其他 agent 的执行能力差异。
科学 authority、round/seal/evidence 边界、手稿作用域仍由
`CLAUDE.md` + `skills/kundur-round/SKILL.md` 决定。

## Startup

1. 只读一次规则。运行时若已按来源标注注入 `AGENTS.md` 或
   `CLAUDE.md`, 它就是已读上下文; 只补读未注入的必需文件。
2. 执行 lane 及 `session_context.py` 边界只由 `AGENTS.md` 定义;
   这里不叠加第二套启动仪式。
3. 当前用户提示定义本次任务。`session_context` 提供需保护的研究
   状态, 不把用户明示的、与活跃证据作用域不相交的 `scratch`
   任务偷换成“继续实验”。先报保护边界, 完成插入任务后只回到
   仍未完成的明示任务队列。
4. 首次写入前记录 `git status --short --branch`; 已有改动视为用户或其他
   运行中任务所有, 只改本任务明确拥有的路径。

## Capability branches

- **File edit**: 在首次修改前读取精确目标; 创建前先确认目标不存在。
  用当前运行时已有的 patch/replace 工具; 若报 stale match /
  read-before-write, 重读该文件一次、重新计算补丁, 不盲目重试。
- **Structured tool**: 按工具当前 schema 发送 lossless JSON/object。参数绑定拒绝后
  先核对必填字段和类型, 用最小调用重发; 不把 shell 文本塞进
  结构化参数来猜语法。
- **Windows shell**: 用 PowerShell 原生命令从头到尾处理路径和进程。
  终端 inspection 能力不可用时, 用运行时 job 状态、`Get-Process`、
  `Get-CimInstance` 或仓库状态工具; 不重试不支持的调用。
- **CLI misuse**: 首次 usage/argument 错误后运行一次 `--help`, 然后只重发
  一条精确命令。领号工具仍保持原子性, 不因 CLI 错误手挑 id。
- **Independent review**: 正式证据/发表门要求独立审查时, 用可用的
  subagent/workflow 对同一冻结提交与哈希审查。无独立执行能力就报告
  该门未满足, 不在一个上下文里角色扮演两个 reviewer。scratch
  自查使用固定 diff, 不需要为此创建提交。

## Long tasks

1. 预计 >5min 的任务用运行时 background/job 能力; 启动前查同名
   进程与输出路径, 启动后等完成事件, 不轮询。
2. Windows 启动 WSL 长流水线时优先用维护入口
   `scripts/launch_detached.py`; 它能避免 WSL 因无前台 holder 而退出,
   但不保证在整个 agent 会话被杀后继续存活。需要跨会话存活时,
   只用已授权的操作系统级服务或计划任务。
3. 正式仿真仍须满足 active plan 的 seal、capacity、rehearsal 和 owner gate;
   运行时更方便不等于科学授权。

## Communication

- 先说结论与因果关系, 再给核对路径。保留必要的电力系统、控制与
  统计术语, 首次出现时说明它在当前论证中的作用。
- 可以从仓库发现的信息直接查。只在答案会改变方案、需要新权限或
  外部输入时问 owner, 且一次只问一个问题。
- 对话中的通俗解释不改写仓库技术资产; 技术文件继续 caveman 短句 + 指针。

## Completion check

- 没有因规则被同一运行时注入而重复整篇读取。
- 没有重试已知不支持的工具路径。
- 没有覆盖、清理、提交或改写非本任务所有的工作区。
- 没有把运行时可用性误当成证据权威或实验授权。
