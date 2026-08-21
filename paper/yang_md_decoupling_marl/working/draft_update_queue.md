# Draft update queue — yang-md-decoupling-marl

草稿批次更新契约的实例。单一真源 = 各 feed 的 `Manuscript mapping` 段
(feed_check 强制存在)；本文件只持指针与已知冲突点，不复制 feed 结论。

## 状态

- 草稿批次更新只在批次节点执行：manuscript lane 轮 / manuscript-refresh /
  提交冻结（CLAUDE.md 手稿线生命周期）。
- 当前：等 R471 (U2 source factorial) 结果后一次性处理。
- 待对照 feed（最新 → 旧）：R469, R468, R467, R465, R464, R463 —
  逐条对照各自 `Manuscript mapping` 段。
- 已知冲突点：R464 (U1 Youla 证书) vs 草稿 §3.5 / §6.4 的「只有蓝图、
  没有证书」表述 — 批次更新时必须修订草稿这两处。

## 使用

- 批次更新时：逐条对照队列中 feed 的 Manuscript mapping 段，改完删除
  对应行。
- 新 feed 完成：只写 feed 的 Manuscript mapping 段；mapping 断言与草稿
  现有文字冲突时 feed 当场标 `CONFLICT`（历史 feed 不回填）。
