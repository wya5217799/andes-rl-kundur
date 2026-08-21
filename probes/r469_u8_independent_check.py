"""Independent NumPy checker for the persisted R469 projector and lift data."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

HORIZON = 30
QC = np.ones(4) / 2.0
TD = np.asarray(
    [
        [0.5, 0.5, -0.5, -0.5],
        [2**-0.5, -(2**-0.5), 0.0, 0.0],
        [0.0, 0.0, 2**-0.5, -(2**-0.5)],
    ]
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check(root: Path) -> dict[str, object]:
    index = json.loads((root / "parameter_points/index.json").read_text(encoding="utf-8"))
    max_lift_error = 0.0
    checked = 0
    for row in index:
        raw = np.load(root / row["npz"], allow_pickle=False)
        stored = np.load(root / row["lift_npz"], allow_pickle=False)["H"]
        a, b, c, d = (
            raw[key] for key in ("A_post_quotient", "B_post_quotient", "C_post_quotient", "D_post")
        )
        reconstructed = np.zeros((HORIZON * 3, HORIZON))
        for column in range(HORIZON):
            state = np.zeros(a.shape[0])
            for step in range(HORIZON):
                scalar = float(step == column)
                command = QC * scalar
                reconstructed[step * 3 : (step + 1) * 3, column] = TD @ (
                    c @ state + d[:, :4] @ command
                )
                state = a @ state + b[:, :4] @ command
        max_lift_error = max(max_lift_error, float(np.max(np.abs(reconstructed - stored))))
        checked += 1
    projectors = np.load(root / "contracts/projectors.npz", allow_pickle=False)
    projector_error = max(
        float(np.linalg.norm(projectors[name] @ projectors[name] - projectors[name]))
        for name in ("P_u", "Q_u", "P_y", "Q_y")
    )
    return {
        "checked_points": checked,
        "maximum_direct_impulse_lift_error": max_lift_error,
        "maximum_projector_idempotence_error": projector_error,
        "passed": bool(checked == 32 and max_lift_error <= 1.0e-10 and projector_error <= 1.0e-12),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--write", type=Path)
    args = parser.parse_args()
    result = check(args.root)
    if args.write:
        if args.write.exists():
            raise FileExistsError(args.write)
        args.write.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        digest = _sha256(args.write)
        Path(f"{args.write}.sha256").write_text(f"{digest}  {args.write.name}\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    if not result["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
