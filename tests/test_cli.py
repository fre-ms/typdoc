"""The command line: what typdoc binds, one answer whatever happens, two files and nothing
anywhere else, the same PDF again from the configuration document, failures by kind
without paths."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from typdoc import __version__
from typdoc.cli import INTERFACE, main

PATIENT = "Mustermann,Erika_1964-08-12_K7Q4MX"


def _answer(capsys: pytest.CaptureFixture[str], argv: list[str]) -> tuple[int, dict, str]:
    status = main(argv)
    captured = capsys.readouterr()
    return status, json.loads(captured.out), captured.err


def test_about(capsys: pytest.CaptureFixture[str]) -> None:
    status, answer, _ = _answer(capsys, ["about"])
    assert status == 0
    assert answer == {"interface": INTERFACE, "made_with": f"typdoc {__version__}",
                      "version": __version__, "standard": "https://medrds.org/spec/0.15",
                      "pictures": ["jpg", "jpeg", "png", "tif", "tiff", "heic", "heif", "webp",
                                   "bmp", "gif"],
                      "to": ["pdf"]}


def test_run_on_the_command_line(tmp_path: Path, jpeg: bytes, png: bytes) -> None:
    """``python -m typdoc run``: progress per picture, two files in the folder and nothing
    in the temporary, home or cache folder, the same again from the configuration."""
    source = tmp_path / PATIENT
    source.mkdir()
    (source / "seite-1.jpg").write_bytes(jpeg)
    (source / "seite-2.png").write_bytes(png)
    elsewhere = {name: tmp_path / name for name in ("tmp", "home", "cache")}
    for folder in elsewhere.values():
        folder.mkdir()
    env = {**os.environ, "TMPDIR": str(elsewhere["tmp"]), "TEMP": str(elsewhere["tmp"]),
           "TMP": str(elsewhere["tmp"]), "HOME": str(elsewhere["home"]),
           "USERPROFILE": str(elsewhere["home"]), "XDG_CACHE_HOME": str(elsewhere["cache"]),
           "PYTHONDONTWRITEBYTECODE": "1"}

    def run(argv: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-m", "typdoc", *argv], capture_output=True,
                              text=True, check=False, env=env)

    first = run(["run", str(source / "seite-1.jpg"), str(source / "seite-2.png"),
                 "--out", str(tmp_path / "out"), "--progress"])
    assert first.returncode == 0, first.stdout
    answer = json.loads(first.stdout)
    assert answer["pages"] == 2 and [b["attached"] for b in answer["bound"]] == [False, True]
    assert all(len(b["sha256"]) == 64 and set(b) == {"sha256", "attached"}
               for b in answer["bound"])
    assert [json.loads(z) for z in first.stderr.splitlines()] == [
        {"page": 1, "of": 2}, {"page": 2, "of": 2}]
    assert sorted(p.name for p in (tmp_path / "out").iterdir()) == [
        "seite-1.pdf", "seite-1.typdoc.json"]
    assert sorted(p.name for p in source.iterdir()) == ["seite-1.jpg", "seite-2.png"]
    for name, folder in elsewhere.items():
        assert not any(folder.rglob("*")), name
    again = run(["run", str(source / "seite-1.jpg"), str(source / "seite-2.png"),
                 "--out", str(tmp_path / "again"), "--config", answer["config"]])
    assert again.returncode == 0, again.stdout
    for key in ("document", "config"):
        assert Path(json.loads(again.stdout)[key]).read_bytes() == Path(answer[key]).read_bytes()
    beside = run(["run", str(source / "seite-1.jpg")])  # without --out: beside the picture
    assert beside.returncode == 0
    assert Path(json.loads(beside.stdout)["document"]).parent.name == "seite-1.typdoc"


def test_failures_without_paths(tmp_path: Path, jpeg: bytes,
                                capsys: pytest.CaptureFixture[str]) -> None:
    folder = tmp_path / PATIENT
    folder.mkdir()
    good = folder / f"{PATIENT}.jpg"
    good.write_bytes(jpeg)
    other = folder / "anders.jpg"
    other.write_bytes(jpeg + b"\0")
    broken = folder / "kaputt.typdoc.json"
    broken.write_text("{kaputt", encoding="utf-8")
    status, made, _ = _answer(capsys, ["run", str(good), "--out", str(tmp_path / "ok")])
    assert status == 0
    cases = {
        "missing": ["run", str(folder / "fehlt.jpg")],
        "unsupported": ["run", str(broken)],
        "bad-config": ["run", str(good), "--config", str(broken)],
        "config-mismatch": ["run", str(other), "--config", made["config"]],
        "usage": ["run", str(good), "--config", made["config"], "--to", "pdf"],
    }
    for kind, argv in cases.items():
        status, answer, err = _answer(capsys, argv)
        assert status == 2 and answer["error"] == kind, kind
        assert set(answer["message"]) == {"en", "de"}
        said = json.dumps(answer, ensure_ascii=False) + err
        assert PATIENT not in said and str(tmp_path) not in said, kind
    status, answer, _ = _answer(capsys, ["run"])
    assert status == 2 and answer["error"] == "usage"
