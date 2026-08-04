# R303 verdict — projection coupling classically closed

**Date**: 2026-08-03
**Status**: COUPLING-CLASSICALLY-CLOSED
**Type**: deterministic-analysis
**Claim**: CLM-0725
**Question**: Q-0060 -> closed-positive

## TL;DR

Heterogeneous per-device projection can leak a zero-sum differential request
into common active power, but the registered endpoint-local classical
allocator closes this controller-coordinate seam. Neural training remains
blocked, and R303 does not support the MARL or VSG-actuator terms in the ICEMS
title.

## Questions opened (this round)

- Q-0060 — heterogeneous-headroom projection coupling and local repair.

## Questions closed (this round)

- Q-0060 -> closed-positive by CLM-0725: material leakage reproduced and
  classically closed.

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这轮干了啥**：没有直接训练网络，而是把公共有功和固定 2Kv 差分请求送入四类异质功率、爬坡与 SOC 裕度，再比较设备独立投影、只看边两端余量的两阶段局部分配器和集中式零和投影 oracle。

**结果（一句话）**：独立投影在 23/24 个异质 case 出现公共坐标泄漏、22/24 达到预设物质量门槛，但局部经典分配器在 32/32 个 case 保持可行与零和，物质 case 的中位差分保留率为 0.579，因此结论是 `COUPLING-CLASSICALLY-CLOSED`。

**意外**：真正的问题不是差分控制器投影前不解耦，而是设备各自饱和后破坏零和；更重要的是，这个缺口不需要神经网络，端点局部 headroom 信息配合反对称边流已经足够关闭。

**我默认下一步做**：停止在这个机制上训练智能体或继续拓扑扫参，转去单独审查会议标题与执行器是否对齐；R303 只支持受限的“decoupling-oriented”控制接口，不支持 MARL 价值，也不直接作用于 VSG。

**你想插一脚就说**：若你坚持保留现有标题，下一步必须先定义真正的 VSG 本地动作和一个经典分布式控制解决不了的残余机制，再 prospectively 冻结匹配的单网络/多网络比较；否则应优先收缩标题与结论。

Feed: `results/r303_projection_coupling/FEED.md`
