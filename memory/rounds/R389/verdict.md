# R389 verdict -- valid negative stock-REGF2 object gate

**Date**: 2026-08-14
**Status**: completed - `STOP-REGF2-OBJECT-INITIALIZATION`
**Type**: experiment
**Wall**: sub-second formal scientific trajectory; one-arm object/initialization gate

## TL;DR

R389 validly stops the exact installed-default stock-REGF2 formulation: the
four-device object constructs and initializes cleanly, but it fails the
prospectively registered no-exogenous-action stationarity gate over 0.2 seconds.

## Questions opened (this round)

- Q-0107: stock-REGF2 object construction, initialization, and short-horizon
  stationarity on the unchanged Kundur network.

## Questions closed (this round)

- Q-0107 closed-negative by CLM-1090: the exact stock-REGF2 formulation fails
  its registered no-exogenous-action stationarity gate before authority.

## Questions advanced (this round, status unchanged)

- (none)

Feed: `paper/converter_vsg_pq_decoupling/reports/R389.md`

## Technical disposition

- Source/case identity, structural absence, four-device/PLL mapping,
  input/runtime parameter cards, references, native initialization, complete
  diagnostics, finite values, 0.2-second completion, and all broad electrical
  envelopes pass.
- The sole failed gate is no-exogenous-action stationarity. The exact sealed
  trace contains a coherent growing sampled pattern, but it does not identify
  a physical mode or distinguish physical dynamics from correlated
  numerical/model-solver behavior.
- Stop stock REGF2 before Paux/Qaux authority, deterministic decoupling,
  controller comparison, or learning. A mechanism-only equilibrium study or
  another converter object requires a new prospective route decision.

## 给 PI 的话

**发生了什么**：我们把四台新的设备接到原有网络后，初始计算和短时运行都能完成，所有数值也保持在宽范围内。但在没有额外操作和扰动时，功率和电压仍持续偏离初始状态，并超过了事先规定的小漂移范围。

**这说明什么**：这套现成设备方案虽然能建立并运行，却不能满足进入下一阶段所需的稳定静止条件。现有记录只能确认偏离呈连续放大，不能确定是设备自身变化还是计算方法共同造成，也不能说明所有同类设备都不可用。

**下一步做什么**：停止在这套现成方案上测试调节能力、控制方法和学习方法。若继续，应先在初始状态附近研究偏离为何放大，区分设备自身变化与计算方法的影响，再决定是否值得开启新的设备方案。
