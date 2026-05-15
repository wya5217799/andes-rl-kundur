"""ANDES DAE introspection + tolerant attribute readers.

These three functions answer one recurring question:
    "I added an ANDES model (TurbineGov / Exciter / PSS / DC line / ...) to ss
     and ss.setup() didn't crash. Is the model actually integrated into the
     DAE solver, or is it a dangling parameter container?"

Decision rule (R10 governor forensic, 2026-05-07):
    - ``introspect_model(ss, "IEEEG1")["readable_vars"]`` — count entries
      whose ``kind`` is one of {"Algeb", "State", "ExtAlgeb", "ExtState"}.
    - 0 Algeb/State = model is NOT in the DAE. Static .add() succeeded but
      ss.setup() either was skipped (e.g. ``except: pass`` swallowed the
      fatal "already setup" error) or the model registration was rolled
      back. Symptom: TDS runs but the model never affects state evolution.
    - >0 Algeb/State = model is integrated. Then check trajectory deltas
      (V_with_model vs V_without_model) for actual physical effect.

Pattern: any "add IEEEG1 / EXST1 / ESST3A / TGOV1 / PSS2A / ...
in v3+/v4+ env" change should be probed with these utilities BEFORE
declaring the wiring fix done.
"""
from __future__ import annotations

from typing import Any, Iterable

import numpy as np


def safe_get(obj: Any, attr: str) -> Any:
    """Tolerant ``getattr(obj, attr)`` — return None on any exception."""
    try:
        return getattr(obj, attr)
    except Exception:
        return None


def try_read_v(
    model: Any, attr_candidates: Iterable[str]
) -> tuple[str | None, list | None]:
    """Try reading ``.v`` from a list of candidate attribute names.

    Returns ``(attr_name, list_of_values)`` for the first attr that yields a
    non-empty numeric array. ``(None, None)`` if no candidate matches.

    Useful when an ANDES model can expose its output under different names
    across versions (IEEEG1: ``pout`` / ``Pgv`` / ``Pmech`` / ``tm`` etc.).
    """
    if model is None:
        return None, None
    for cand in attr_candidates:
        v = safe_get(model, cand)
        if v is None:
            continue
        vv = safe_get(v, "v")
        if vv is None:
            continue
        try:
            arr = list(np.asarray(vv).copy())
        except Exception:
            continue
        if len(arr) == 0:
            continue
        return cand, arr
    return None, None


def introspect_model(
    ss: Any, model_name: str, top_n: int = 25
) -> dict[str, Any]:
    """List numeric ``.v`` readable vars on an ANDES model.

    Args:
        ss: ``andes.System`` instance (post ``ss.setup()`` and ``ss.PFlow.run()``).
        model_name: top-level model attribute, e.g. ``"GENROU"``, ``"IEEEG1"``,
            ``"EXST1"``, ``"PQ"``.
        top_n: cap on returned readable_vars (sorted size desc, attr asc).

    Returns:
        ``{"model": str, "found": bool, "n": int, "readable_vars": [...]}``

        Each ``readable_vars`` entry: ``{"attr", "size", "first", "kind"}``
        where ``kind`` is the class name of the wrapping object (``Algeb``,
        ``State``, ``ConstService``, ``NumParam``, ``IdxParam``, ``FlagValue``,
        etc.). Use ``kind`` to discriminate DAE-level vars from constants.

    DAE-active heuristic:
        ``num_dae = sum(1 for v in result["readable_vars"]
                        if v["kind"] in {"Algeb", "State",
                                         "ExtAlgeb", "ExtState"})``
        ``num_dae > 0`` → model is integrated into DAE.
        ``num_dae == 0`` → model is a parameter container only (NOT in DAE).
    """
    out: dict[str, Any] = {"model": model_name}
    model = safe_get(ss, model_name)
    if model is None:
        out["found"] = False
        return out
    out["found"] = True
    out["n"] = safe_get(model, "n")
    readable: list[dict[str, Any]] = []
    for attr in dir(model):
        if attr.startswith("_"):
            continue
        v = safe_get(model, attr)
        if v is None:
            continue
        vv = safe_get(v, "v")
        if vv is None:
            continue
        try:
            arr = np.asarray(vv)
        except Exception:
            continue
        if arr.dtype.kind not in "fiub":
            continue
        if arr.size == 0:
            continue
        readable.append(
            {
                "attr": attr,
                "size": int(arr.size),
                "first": float(arr.flat[0]) if arr.size else None,
                "kind": type(v).__name__,
            }
        )
    readable.sort(key=lambda r: (-r["size"], r["attr"]))
    out["readable_vars"] = readable[:top_n]
    return out
