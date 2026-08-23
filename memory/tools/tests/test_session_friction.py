"""Tests for session_friction.py --artifact (external DSH session exports).

Motivation: an external agent (Codex, 2026-08-23) had to hand-extract a DSH
session zip into tmp/ before it could run the friction census. The tool now
accepts a .zip bundle, a plain .jsonl session, or a .zstd/.zst artifact
directly; these tests pin that entry point and its graceful failure modes.
"""
import json
import zipfile

import pytest

from memory.tools import session_friction as sf


def _session_text():
    header = {"type": "session", "version": 0, "id": "test-sess-1",
              "cwd": "E:\\Projects\\andes-rl-kundur"}
    lines = [json.dumps(header)]
    lines.append(json.dumps({"type": "user/message", "data": {"content": [
        {"type": "text", "text": "说人话讲解最新成果怎么样"}]}}))
    lines.append(json.dumps({"type": "tool/result", "data": {"message": {"content": [
        {"type": "tool-result", "content": [
            {"type": "text",
             "text": 'Error: edit requires reading "x.py" first — read the file, then retry'}]}]}}}))
    lines.append(json.dumps({"type": "tool/result", "data": {"message": {"content": [
        {"type": "tool-result", "content": [
            {"type": "text", "text": "usage: reserve_claim.py [-h] [--claims-dir CLAIMS_DIR]"}]}]}}}))
    return "\n".join(lines) + "\n"


def test_artifact_plain_jsonl_scans(capsys):
    import pathlib
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        f = pathlib.Path(d) / "session.jsonl"
        f.write_text(_session_text(), encoding="utf-8")
        rc = sf.main(["--artifact", str(f)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "edit-fail" in out
    assert "cli-usage" in out
    assert "说人话" in out
    assert "sessions=1" in out


def test_artifact_zip_scans(tmp_path, capsys):
    zpath = tmp_path / "session.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("session.jsonl", _session_text())
    rc = sf.main(["--artifact", str(zpath)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "edit-fail" in out
    assert "sessions=1" in out


def test_artifact_bad_zip_exits_1(tmp_path, capsys):
    zpath = tmp_path / "broken.zip"
    zpath.write_bytes(b"this is not a zip file")
    rc = sf.main(["--artifact", str(zpath)])
    err = capsys.readouterr().err
    assert rc == 1
    assert "no session text" in err


def test_artifact_missing_exits_1(tmp_path, capsys):
    rc = sf.main(["--artifact", str(tmp_path / "nope.jsonl")])
    err = capsys.readouterr().err
    assert rc == 1
    assert "artifact not found" in err
