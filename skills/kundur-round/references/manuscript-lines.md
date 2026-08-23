# Manuscript lines — 手稿线作用域与文档生命周期 (从 CLAUDE.md 下放, 2026-08-23)

步骤走 `skills/kundur-round/SKILL.md` §5; 本文件持契约细节.

## LINE.md

- 每篇一个 `paper/<line>/LINE.md`: 状态、优先级、读写作用域、当前目标与 venue gate. 只做导航, 不复制 Deep Research、feed 结论或实验数字.
- `decision_refs` 指向持久决策; `evidence_refs` 绑定 claim 与 feed; authoritative feed 禁止进入 `required_reading`, 按 claim 懒加载.
- `verification` 段是 schema 强制项, 只许放通用执行规则或"事实在 feed"指针, 禁止逐轮复述结论/数字; 每轮只增一条 `evidence_refs`.
- 接近导航预算时先压 `verification`/`stop_when` 复述, 不裁 `evidence_refs` 指针.
- `active` 是生命周期状态, 不是全局唯一主线; 多条在写论文可以同时 active.
- 用户明确提到某篇论文 → `session_context.py --line <id>` 显式选择; 未知 id → `--list-lines`; 未指定论文才按 `priority` 回退. 切线不得冻结别的论文、改优先级或搬运证据.
- 预算 (contract.json): line_max_lines 90 / line_max_bytes 8192.

## ARTIFACTS.json

- 每篇一个: 登记需要持久化的调研、决策、草稿、图、审稿汇总与交付资产. 未登记的过程输出默认住 `tmp/`.
- 审稿: 细分 reviewer 报告默认临时, 只在产生长期行动或需要审计追踪时登记一份 consolidated review. 每种 purpose 只允许一个 active canonical.

## 作用域

- 一条手稿线默认只能写自己的 `write_roots`. 来源会议稿、共享 results 与 memory 只读; 要改另一篇稿子必须单独选择并授权那条线.
- Deep Research: 只服务一篇 → 登记该线; 跨线可复用 → `docs/research/`; 探索性输出留 `tmp/`.

## 时间敏感

- 时间敏感文档必须有 `review_after`; 输入变化或到期后标 `stale`/`superseded`, 禁止继续作为当前决策依据.
- 冷启动切换 `manuscript-refresh`, 直到 `repo_health.py check --no-baseline` 清除过期或输入漂移错误.

## 哈希快照与批次更新

- 有 authoritative `experiment-feeds` 的线, active `line-state` 必须在 ARTIFACTS.json 对 feed 目录做哈希快照.
- 新 feed/旧 feed 变化必须先触发 `manuscript-refresh`; 把最新 feed 绑定进 `evidence_refs`、核对 LINE 当前动作与受影响 artifact 输入后才能刷新哈希, 禁止只更新 hash 值.
- 草稿本体只在批次节点更新 — manuscript lane 轮 / manuscript-refresh / 提交冻结; feed 收尾不改稿 (SKILL.md §2-g).
- feed 的 `Manuscript mapping` 段 = 草稿待更新清单单一真源 (feed_check 强制); 批次更新时逐条对照, 不另建清单副本.
- mapping 断言与草稿现有文字冲突 → feed 当场标 `CONFLICT` 防漏改.
- 草稿滞后于最新 feed = 正常状态; 证据权威在 feed/claim, 草稿只是出口.
