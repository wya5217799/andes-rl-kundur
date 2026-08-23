from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import external_theory_intake_lint as lint  # noqa: E402


def _line(root: Path, folder: str, line_id: str) -> Path:
    line_root = root / "paper" / folder
    line_root.mkdir(parents=True)
    (line_root / "LINE.md").write_text(
        f"---\nline_id: {line_id}\n---\n",
        encoding="utf-8",
    )
    return line_root


def test_find_feed_resolves_registered_line_id_not_folder_spelling(
    tmp_path: Path, monkeypatch,
) -> None:
    monkeypatch.setattr(lint, "ROOT", tmp_path)
    line_root = _line(tmp_path, "yang_md_decoupling_marl", "yang-md-decoupling-marl")
    report = line_root / "reports" / "R476.md"
    report.parent.mkdir()
    report.write_text("supported\n", encoding="utf-8")
    plan = "manuscript_line: yang-md-decoupling-marl\n"

    assert lint._find_feed("R476", plan) == str(report)


def test_find_feed_does_not_fall_back_to_unrelated_feed_for_registered_line(
    tmp_path: Path, monkeypatch,
) -> None:
    monkeypatch.setattr(lint, "ROOT", tmp_path)
    _line(tmp_path, "yang_md_decoupling_marl", "yang-md-decoupling-marl")
    unrelated = tmp_path / "results" / "r288_topology_information" / "FEED.md"
    unrelated.parent.mkdir(parents=True)
    unrelated.write_text("old feed\n", encoding="utf-8")
    plan = "manuscript_line: yang-md-decoupling-marl\n"

    assert lint._find_feed("R476", plan) is None
