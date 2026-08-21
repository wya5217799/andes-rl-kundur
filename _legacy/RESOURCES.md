# ANDES VSG 控制研究栈资源

## Knowledge

- [R271 执行器权威审计](memory/rounds/R271/verdict.md)
  当前 M/D-only VSG 为什么擅长瞬态、却缺少持续共同频率恢复能力；用于理解为什么需要独立有功通道。
- [R272 有功执行器实验](memory/rounds/R272/verdict.md)
  四台 VSG 代理与四台 ESD1 储能、经典 droop+PI、SOC/功率约束的正式定义；用于区分 VSG、储能和 AI。
- [R273 失败归因](memory/rounds/R273/verdict.md)
  原始 V4 与零指令储能 DAE 的对照；用于理解当前一轮为什么完全没有运行 AI 或 PI。
- [储能环境源码](src/andes_rl_kundur/env/andes/andes_vsg_storage_env.py)
  项目中储能功率请求、SOC 和约束如何进入仿真；用于需要代码级核对时。
- [可行性筛选契约](src/andes_rl_kundur/evaluation/feasibility_screen.py)
  为什么必须先筛选环境可完成性、再比较控制器；用于理解研究流程而非控制算法。

## Wisdom (Communities)

- 当前优先使用仓库中的封印实验、claim 和 PI briefing 复核结论。
  外部社区意见不能替代本项目的物理合同与 sealed evaluation。

## Gaps

- 尚未形成统一的“VSG + GFM 储能”物理模型；当前组合是 VSG proxy + 独立 GFL BESS。
- 尚无有效封印证据证明 AI residual 优于合格的经典有功基线。
