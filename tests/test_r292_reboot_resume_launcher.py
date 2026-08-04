from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts/run_r292_formal_v3_resume_after_reboot.sh"


def test_reboot_resume_uses_existing_seal_and_never_reprepares() -> None:
    source = LAUNCHER.read_text(encoding="utf-8")

    assert "audit_r292_formal_v3_resume.py" in source
    assert "run_r292_formal_v3.py prepare" not in source
    assert "recover_r292_fresh_bank" not in source
    assert source.count("run_r292_formal_v3.py run") == 3
    assert "run_r292_formal_v3.py analyse" in source
    assert "formal_v3_seal.json.sha256" in source
    assert "wait_three" in source
    assert "formal_v3_resume1_shard_0.log" in source
    assert "formal_v3_resume1_shard_1.log" in source
    assert "formal_v3_resume1_shard_2.log" in source
