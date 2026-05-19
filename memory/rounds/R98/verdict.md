**Status**: COMPLETE — schema + tools + 23 notes shipped, parallel-session-friendly

## TL;DR
Memory subsystem extended with Note entity (`NOTE-NNNN`) as index layer over external archives. 23 notes ingested across 4 waves (5 ADR + 11 handoff + 2 eng-note/session-report + 5 legacy). X1+X2 coverage warnings dropped 14→0. Tools added: new_note.py, note_query.py; render.py grew `## Archive Index` section. Source files (handoffs/ADRs/_legacy/) byte-identical (spec §9-3 lossless preservation honored).

## Questions opened (this round)

- Q-0023: Will the Archive Index actually be queried in subsequent rounds (signal that lazy claim-extraction is happening)? Success indicator: ≥ 1 claim with `extracted_from: NOTE-NNNN` provenance within 30 days.

## Questions closed (this round)

(none — this is infrastructure, not experimental)

## Questions advanced (this round, status unchanged)

(none)

## 给 PI 的话

**这周干了啥**：基于你"让对话能感知所有过去实验和数据"的需求, brainstorm → spec → plan → 16-task subagent-driven execution, 一口气把记忆系统从"R39 后单纯只看 claim/round/Q"扩展成"还能扫到 R39 之前所有 handoff / ADR / legacy / eng-notes". 全程 feature branch (feature/memory-notes-ingest), 不抢 parallel session 的 R93-R97 工作面.

**结果（一句话）**：23 个 NOTE-NNNN 入仓 (5 ADR + 11 handoff + 2 eng-note/session-report + 5 legacy split notes), X1+X2 coverage warning 14→0, validate/render/note_query 工具链 111 个 pytest 全绿, 8 个 top-level topic bucket 全活, 源文件零修改 (spec §9-3 lossless preservation).

**意外**：(1) Phase B (STATE.md 脏状态修复 R45/R91/R90) 三个全 no-op — parallel session 早就处理过了, 这个 plan 是基于较老的 STATE.md 写的, 实际进入 worktree 时已被 commit `81b19a2`+ 系列收尾. 验证了 brainstorm 时担心的"双 session 协作"风险其实很低 — 各自只动自己的轮次, schema 改动隔离在 feature branch. (2) Wave 4 sweep 是 0 notes (scripts/_archive/ 的 18 个 r0X 驱动早已被 R10/R10-R17 unified verdict 覆盖); 这给"宁少勿多"做了实证. (3) note_query.py 加 `--source` choices 时, code-reviewer 建议 import NOTE_SOURCE_ENUM 而不是硬编码 — 改完是 6 行 diff 但消掉了 schema-CLI drift 隐患, 是 quality 三段式 review 真正发挥的一次.

**我默认下一步做**：(1) **Phase D 现在执行的就是 R98 收尾本身** — 这个 verdict 写完, paste 给 PI 简报到 chat (ADR-0003 contract), 然后 merge feature branch 到 main. (2) merge 完默认转回 parallel session 的 R96/R97 active work (那俩是 in-flight, 不是这个 schema 工作). (3) Q-0023 在 30 天观察窗内自然 close — 看是否真有 round 开始用 note_query.py 检索老内容.

**你想插一脚就说**：(a) 想看某个 NOTE 内容质量 — 说 "看 NOTE-XXXX"; (b) 想加更多 topic 顶层 bucket (现在 8 个 closed 是否够) — 说 "加 topic XXX"; (c) 想把 X1/X2 从 warning 升级成 ERROR (强制每个新 handoff/ADR 必须配 note) — 说 "X 升级"; (d) merge 策略上 想 rebase 还是 merge commit — 说 "rebase / merge". 默认 **merge commit 保留 16-task 轨迹**.
