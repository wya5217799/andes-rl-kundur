from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

import numpy as np

from andes_rl_kundur.evaluation.full_order_bridge_bundle import (
    archive_full_order_bridge_bundle,
    build_full_order_bridge_bundle,
    verify_full_order_bridge_bundle,
)

ROOT = Path(__file__).resolve().parents[1]


def test_exporter_builds_complete_hs0_hs1_core_bundle(tmp_path: Path) -> None:
    bundle = build_full_order_bridge_bundle(
        repo_root=ROOT,
        output_dir=tmp_path / "full_order_bridge_bundle",
    )

    assert bundle == tmp_path / "full_order_bridge_bundle"
    for point in ("HS0", "HS1"):
        point_dir = bundle / "points" / point
        assert {
            "equilibrium.npz",
            "dae_jacobians.npz",
            "full_order_continuous.npz",
            "full_order_discrete.npz",
            "variable_catalog.json",
            "linearization_convention.json",
            "finite_difference_audit.csv",
        } <= {path.name for path in point_dir.iterdir()}

        equilibrium = np.load(point_dir / "equilibrium.npz")
        np.testing.assert_allclose(equilibrium["d0_load"], [11.59, 15.75, 2.48, 0.05])
        assert equilibrium["x0"].shape == (122,)
        assert equilibrium["y0"].shape == (376,)
        assert equilibrium["u0_node"].shape == (4,)
        assert equilibrium["u0_coord"].shape == (4,)
        assert equilibrium["output0_omega4"].shape == (4,)
        assert equilibrium["output0_coord4"].shape == (4,)

        jacobians = np.load(point_dir / "dae_jacobians.npz")
        assert jacobians["E"].shape == (122, 122)
        assert jacobians["Fx"].shape == (122, 122)
        assert jacobians["Fy"].shape == (122, 376)
        assert jacobians["Gx"].shape == (376, 122)
        assert jacobians["Gy"].shape == (376, 376)
        assert jacobians["Bx_u_node_scales"].shape == (3, 122, 4)
        assert jacobians["Hy_u_node_scales"].shape == (3, 376, 4)
        assert jacobians["Bx_d_load_scales"].shape == (3, 122, 4)
        assert jacobians["Hy_d_load_scales"].shape == (3, 376, 4)

        continuous = np.load(point_dir / "full_order_continuous.npz")
        assert continuous["A_c"].shape == (122, 122)
        assert continuous["Bu_node_c"].shape == (122, 4)
        assert continuous["Bu_coord_c"].shape == (122, 4)
        assert continuous["Bd_load_c"].shape == (122, 4)
        assert continuous["C_omega4_c"].shape == (4, 122)
        assert continuous["C_coord4_c"].shape == (4, 122)

        discrete = np.load(point_dir / "full_order_discrete.npz")
        assert discrete["A_d"].shape == (122, 122)
        assert discrete["Bu_node_d"].shape == (122, 4)
        assert discrete["Bu_coord_d"].shape == (122, 4)
        assert discrete["Bd_load_d"].shape == (122, 4)
        assert float(discrete["Ts"]) == 0.2

        catalog = json.loads((point_dir / "variable_catalog.json").read_text("utf-8"))
        assert len(catalog["dynamic_states"]) == 122
        assert len(catalog["algebraic_variables"]) == 376
        assert catalog["control_coordinate_inputs"] == [
            "common",
            "edge_0",
            "edge_1",
            "edge_2",
        ]
        assert catalog["load_inputs"] == ["Bus7", "Bus8", "Bus14", "Bus15"]


def test_bundle_hash_verifier_and_upload_archive_cover_the_public_delivery(tmp_path: Path) -> None:
    bundle = build_full_order_bridge_bundle(
        repo_root=ROOT,
        output_dir=tmp_path / "full_order_bridge_bundle",
    )

    assert verify_full_order_bridge_bundle(bundle) == {"pass": True, "failures": []}
    archive = archive_full_order_bridge_bundle(
        bundle,
        tmp_path / "full_order_bridge_bundle_for_gpt.zip",
    )
    with zipfile.ZipFile(archive) as handle:
        assert handle.testzip() is None
        names = set(handle.namelist())
    assert "full_order_bridge_bundle/manifest.json" in names
    assert "full_order_bridge_bundle/points/HS0/dae_jacobians.npz" in names
    assert "full_order_bridge_bundle/points/HS1/full_order_discrete.npz" in names

    code_refs = (bundle / "code_refs.md").read_text("utf-8")
    match = re.search(
        r"`src/andes_rl_kundur/evaluation/full_order_bridge_bundle.py:(\d+)`"
        r" — `def build_full_order_bridge_bundle`",
        code_refs,
    )
    assert match is not None
    source_line = (
        (ROOT / "src/andes_rl_kundur/evaluation/full_order_bridge_bundle.py")
        .read_text("utf-8")
        .splitlines()[int(match.group(1)) - 1]
    )
    assert source_line.startswith("def build_full_order_bridge_bundle")

    readme = bundle / "README.md"
    readme.write_text(readme.read_text("utf-8") + "tampered\n", encoding="utf-8")
    verification = verify_full_order_bridge_bundle(bundle)
    assert verification["pass"] is False
    assert "hash mismatch: README.md" in verification["failures"]
