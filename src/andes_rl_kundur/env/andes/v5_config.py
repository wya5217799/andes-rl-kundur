"""Per-instance configuration for ``AndesMultiVSGEnvV5`` (R80+).

V5 = V4 plant + REGCA1 风机. V4 plant 把 G4 用 GENROU+ZERO_G4_INERTIA hack
当风机, W2 用 GENCLS M=0.1 当风机. R80 grill (ADR-0004) 把两个 plant
风机一起换成 ANDES REGCA1+REECA1 industry-standard 模型, 与 V4 并存.

Framing 是 **ANDES 侧 plant 颗粒度工程升级, paper-deviation** ——
paper Sec.II 显式 "neglect inner loop", REGCA1 反方向; paper Sec.IV-A
风机模型沉默, "对齐 paper" 无据. V5 contribution path 阶梯 C3→C2→C1,
按结果定. 详见 docs/adr/0004-v5-env-regca1-plant-paper-deviation.md.

V5Config 继承 V4Config (所有 reward / action / R58 audit 字段不变),
加 3 个 V5 专属字段控制 plant 风机模型.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .v4_config import V4Config


@dataclass(frozen=True)
class V5Config(V4Config):
    """Per-instance V5 env configuration. Defaults = REGCA1 plant.

    Inherits all V4Config fields (vsg_m0/d0, phi_*, action range, R58
    audit knobs). Adds 3 plant 风机 knobs.
    """

    # ─── 风机 plant 模型 (ADR-0004) ─────────────────────────────────
    # "regca1"          = G4 + W2 都换 ANDES REGCA1+REECA1 (paper-忠实
    #                     的两边一起换, 但 R80 cycle 3a/3c 实测在 100 MVA
    #                     base + G4 700 MW (Ipcmd=7.0 接近 Imax=10) +
    #                     G4 GENROU u=0 disable 留下 TGOV1 init residual
    #                     7.56 → TDS t=2.0s 步长压零, 不可用)
    # "regca1_w2_only"  = (V5 default, cycle 3c GREEN) 只换 W2 REGCA1+
    #                     REECA1, G4 保留 V4 GENROU + ZERO_G4_INERTIA hack.
    #                     W2 100 MW @ 100 MVA base → Ipcmd ≤ 1.0, 远小于
    #                     Imax=10, 不触限. G4 链不动 → 无 TGOV1 init residual.
    # "gencls"          = V5 fallback to V4 plant 完整 (退路)
    wind_model: Literal["regca1", "regca1_w2_only", "gencls"] = "regca1_w2_only"

    # ─── REGCA1 容量 ──────────────────────────────────────────────────
    # G4: Kundur 经典 700 MW 同步机, Sn=900 MVA base. paper Sec.IV-A
    # "wind farm with the same capacity" 不指定 wind base, 我们保留
    # ANDES Kundur GENROU 的 Sn=900 让 REGCA1 接到同一 PV slot 不破能量平衡.
    g4_regca1_sn: float = 900.0
    # W2: paper Sec.IV-A "100 MW wind farm" → Sn=100 跟 V4 GENCLS M=0.1
    # 用的 WF2_SN=100 一致.
    wf2_regca1_sn: float = 100.0

    def __post_init__(self) -> None:
        # 先跑 V4Config 的 validation (action_penalty_mode / obs flags / R58 audit)
        super().__post_init__()
        if self.wind_model not in ("regca1", "regca1_w2_only", "gencls"):
            raise ValueError(
                f"wind_model must be 'regca1' / 'regca1_w2_only' / 'gencls', "
                f"got {self.wind_model!r}"
            )
        if self.wind_model == "regca1" and self.zero_g4_inertia:
            # 这俩是互斥的: regca1 模式下 G4 GENROU 整链 disable, ZERO_G4_INERTIA
            # 的 M/D tweak hack 完全 moot. 不抛错, 但要明确语义 — 我们不
            # 修改 frozen field, 让 V5 env _build_system 跳过 ZERO_G4_INERTIA 路径.
            pass

    # ─── Factory methods ─────────────────────────────────────────────

    @classmethod
    def v5_default(cls) -> V5Config:
        """V5 默认 — W2 换 REGCA1, G4 保留 V4 hack (cycle 3c GREEN).

        Cycle 3a 实测 "G4+W2 同时换 REGCA1" 在 Kundur 100 MVA base 下:
        G4 700 MW → Ipcmd=7.0 接近 Imax=10, 加上 G4 GENROU u=0 disable 留下
        TGOV1 init residual 7.56 + REGCA1 HVG_x clamped → 7 步 TDS 步长压零.
        Cycle 3c minimal-impl: 退到 W2-only REGCA1 升级 (paper 100 MW W2,
        Ipcmd ≤ 1.0 远小于 Imax=10, 不触限). G4 保留 V4 ZERO_G4_INERTIA hack.

        这跟 paper "G4 replaced by wind farm with same capacity" 仍有偏差
        (G4 用 GENROU+H≈0 假风机), 但 paper Sec.II "neglect inner loop" 声明
        对 GENROU+H=0 反而更宽容. paper-deviation framing 见 ADR-0004.

        想跑 G4+W2 一起换的研究 (例如调小 G4 Sn / 调大 REGCA1 Imax) 见
        wind_model="regca1" 模式 + 后续 round.
        """
        return cls(wind_model="regca1_w2_only")

    @classmethod
    def v5_regca1_both(cls) -> V5Config:
        """G4+W2 全 REGCA1 (R80 cycle 3a 实测不可用, 留作未来研究入口).

        TDS 在 t=2.0 s 步长压零. 后续 round 修需要:
        (a) 调小 G4 REGCA1 Sn (例如 100 MVA), 让 Ipcmd p.u. 减小
        (b) 调大 REECA1 Imax (default 10 → 50), 给 limiter 留 margin
        (c) 用 ANDES System.remove() 真删 G4 GENROU/TGOV1/EXDC2 而非 u=0
        (d) 加 REPCA1 plant-level controller 给 REGCA1 合理 P/Q ref
        """
        return cls(wind_model="regca1")

    @classmethod
    def v4_plant_fallback(cls) -> V5Config:
        """V5 退路 — 退到 V4 plant (GENROU+ZERO_G4_INERTIA + GENCLS W2).

        用于 Phase B (C3 cross-eval) 想看 V5 代码路径下跑 V4 plant 时,
        以验证 V5 scaffold 没污染 baseline. 跟直接用 V4 env 应该 bit-
        identical (模 1e-9), 但 V5 走 subclass 路径不同 import 链.
        """
        return cls(wind_model="gencls", zero_g4_inertia=True)
