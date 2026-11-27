"""The pictures of one document: bound in the order given, named in the PDF by their
place and never by their file's name, made again from the configuration document, and
refused where they are no pictures."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path

import pymupdf
import pytest

from tests.conftest import encoded, letter
from typdoc import output, pictures
from typdoc.errors import TypdocError, describe_error
from typdoc.project import Options, Project, load_config

PATIENT = "Mustermann,Erika_1964-08-12_K7Q4MX"  # a file name as records have them


def _files(folder: Path, jpeg: bytes, png: bytes, heic: bytes) -> list[Path]:
    folder.mkdir(parents=True, exist_ok=True)
    paths = [folder / f"{PATIENT}-1.JPG", folder / f"{PATIENT}-2.png", folder / f"{PATIENT}-3.heic"]
    for path, data in zip(paths, (jpeg, png, heic), strict=True):
        path.write_bytes(data)
    return paths


def test_bound_and_made_again(tmp_path: Path, jpeg: bytes, png: bytes, heic: bytes) -> None:
    paths = _files(tmp_path / "in", jpeg, png, heic)
    project = Project.open(paths)
    bound = project.build()
    first = output.write(bound, tmp_path / "a", "brief")
    assert sorted(p.name for p in (tmp_path / "a").iterdir()) == ["brief.pdf", "brief.typdoc.json"]
    assert bound.attached == [False, True, True]
    assert [entry["name"] for entry in bound.bound] == [
        "picture-1.jpg", "picture-2.png", "picture-3.heic"]
    config = load_config(first["config"])
    assert config == {
        "format": "typdoc-config", "version": 1,
        "made_with": f"typdoc {importlib.metadata.version('typdoc')}",
        "input": {"pictures": [{"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                                "suffix": suffix}
                               for data, suffix in ((jpeg, ".jpg"), (png, ".png"),
                                                    (heic, ".heic"))]},
        "options": {"to": "pdf"}}
    everything = first["document"].read_bytes() + first["config"].read_bytes()
    assert PATIENT.encode() not in everything and b"Mustermann" not in first["config"].read_bytes()
    assert str(tmp_path).encode() not in everything
    again = Project.open(paths, config=config)
    second = output.write(again.build(), tmp_path / "b", "brief")
    for key in ("document", "config"):
        assert first[key].read_bytes() == second[key].read_bytes(), key
    with pymupdf.open(first["document"]) as doc:
        assert len(doc) == 3 and doc.embfile_get("picture-3.heic") == heic


def test_a_configuration_of_other_pictures(tmp_path: Path, jpeg: bytes, png: bytes,
                                           heic: bytes) -> None:
    paths = _files(tmp_path / "in", jpeg, png, heic)
    config = Project.open(paths).config()
    for other in (paths[::-1], paths[:2], [paths[0], paths[0], paths[2]]):
        with pytest.raises(TypdocError) as caught:
            Project.open(other, config=config)
        assert caught.value.kind == "config-mismatch"
    for broken in ({**config, "input": None}, {**config, "input": {"pictures": "alle"}},
                   {**config, "options": {"to": "docx"}}, {**config, "options": None}):
        with pytest.raises(TypdocError) as caught:
            Project.open(paths, config=broken)
        assert caught.value.kind == "bad-config"
    path = tmp_path / "x.typdoc.json"
    path.write_text(json.dumps({**config, "version": 9}), encoding="utf-8")
    with pytest.raises(TypdocError) as caught:
        load_config(path)
    assert caught.value.details == {"reason": "format"}
    assert Options.from_dict({"to": "pdf"}) == Options()


def test_what_a_page_shows_of_a_picture_that_is_no_jpeg(png: bytes, jpeg: bytes) -> None:
    """Upright, transparent parts on white, grey where the picture has no colour; the
    same picture, the same JPEG; a JPEG is shown as it is."""
    from PIL import Image

    assert pictures.shown(jpeg) is None
    shown = pictures.shown(png)
    assert shown is not None and shown == pictures.shown(png)
    import io

    with Image.open(io.BytesIO(shown)) as image:
        assert image.format == "JPEG" and image.mode == "RGB" and image.size == (420, 594)
        assert min(image.getpixel((5, 5))) >= 250  # what was transparent is white
    grey = pictures.shown(encoded(letter(mode="L"), "PNG"))
    assert grey is not None
    with Image.open(io.BytesIO(grey)) as image:
        assert image.mode == "L"
    turned = letter(300, 200)
    exif = Image.Exif()
    exif[0x0112] = 6  # held turned: the page shows it upright
    sideways = pictures.shown(encoded(turned, "PNG", exif=exif))
    assert sideways is not None
    with Image.open(io.BytesIO(sideways)) as image:
        assert image.size == (200, 300) and not image.getexif()


def test_what_is_no_picture(tmp_path: Path, jpeg: bytes) -> None:
    """Each refusal by its kind, worded in both languages, and never with a path."""
    folder = tmp_path / PATIENT
    folder.mkdir()
    pdf = folder / "schon.pdf"
    doc = pymupdf.open()
    doc.new_page()
    doc.save(pdf)
    doc.close()
    word = folder / "brief.docx"
    word.write_bytes(b"PK")
    text = folder / "text.jpg"
    text.write_bytes(b"kein Bild")
    cut = folder / "halb.png"
    cut.write_bytes(encoded(letter(), "PNG")[:200])
    pages = folder / "zwei.tiff"
    letter().save(pages, format="TIFF", save_all=True, append_images=[letter()])
    cases = {"missing": folder / "fehlt.jpg", "not-picture": pdf, "unsupported": word,
             "unreadable": text, "several-frames": pages}
    for kind, path in cases.items():
        with pytest.raises(TypdocError) as caught:
            Project.open([path]).build()
        assert caught.value.kind == kind, kind
        for language in ("en", "de"):
            said = describe_error(caught.value, language)
            assert said and PATIENT not in said and str(tmp_path) not in said
    with pytest.raises(TypdocError) as caught:
        Project.open([cut]).build()
    assert caught.value.kind == "unreadable"
    with pytest.raises(TypdocError) as caught:
        Project.open([])
    assert caught.value.kind == "usage"


def test_a_step_of_docrepro(tmp_path: Path, heic: bytes) -> None:
    """typdoc joins docrepro's chain through its entry point; the adapter opens the
    original picture and hands on the PDF."""
    points = {p.name: p for p in importlib.metadata.entry_points(group="docrepro.steps")}
    adapter = points["typdoc"].load()()
    photo = tmp_path / "foto.heic"
    photo.write_bytes(heic)
    seen: list[tuple[int, int]] = []
    project = adapter.open(photo, None, {"reader": "none"}, tmp_path / "scratch")
    try:
        paths = adapter.write(project, tmp_path / "out", "foto", lambda n, m: seen.append((n, m)))
        config = adapter.config(project)
        assert adapter.dropped(project) == []
    finally:
        adapter.close(project)
    assert seen == [(1, 1)] and paths["document"].name == "foto.pdf"
    assert config["input"]["pictures"][0]["suffix"] == ".heic"
    again = adapter.open(photo, config, {}, tmp_path / "scratch")
    assert adapter.write(again, tmp_path / "again", "foto", None)["document"].read_bytes() \
        == paths["document"].read_bytes()
    assert adapter.version == importlib.metadata.version("typdoc")
