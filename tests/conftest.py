"""Shared fixtures: invented pictures of an invented letter in the formats a phone and a
scanner write, and the reference library of medRDS where it is at hand (``MEDRDS``, else
``../medRDS``)."""

from __future__ import annotations

import base64
import io
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

MEDRDS = Path(os.environ.get("MEDRDS", Path(__file__).resolve().parents[2] / "medRDS"))
LINES = ["Neurologische Sprechstunde Beispiel", "Musterweg 1, 12345 Musterstadt", "",
         "Betr.: Erika Mustermann, geb. 12.08.1964", "",
         "Sehr geehrte Frau Kollegin,", "anbei der Befund vom 12.03.2026.",
         "Kalium 5,8 mmol/l (3,5 - 5,1)", "", "Mit freundlichen Grüßen"]
needs_medrds = pytest.mark.skipif(shutil.which("node") is None or not (MEDRDS / "lib").is_dir(),
                                  reason="needs Node and the reference library of medRDS")


def letter(width: int = 420, height: int = 594, mode: str = "RGB") -> Image.Image:
    """A page of an invented letter as a picture."""
    white = {"RGB": (255, 255, 255), "L": 255, "RGBA": (255, 255, 255, 0)}[mode]
    black = {"RGB": (20, 20, 20), "L": 20, "RGBA": (20, 20, 20, 255)}[mode]
    image = Image.new(mode, (width, height), white)
    draw = ImageDraw.Draw(image)
    for n, line in enumerate(LINES):
        draw.text((30, 40 + 22 * n), line, fill=black)
    draw.rectangle((30, 300, 200, 360), outline=black, width=2)
    return image


def encoded(image: Image.Image, format_: str, **options: object) -> bytes:
    """A picture's bytes in a format."""
    import pillow_heif

    pillow_heif.register_heif_opener()
    buffer = io.BytesIO()
    image.save(buffer, format=format_, **options)
    return buffer.getvalue()


def with_orientation(jpeg: bytes, orientation: int) -> bytes:
    """A JPEG as a camera writes it that was held turned: EXIF orientation ``n``."""
    exif = (b"Exif\0\0" + b"MM\0\x2a\0\0\0\x08" + b"\0\x01"
            + b"\x01\x12\0\x03\0\0\0\x01\0" + bytes([orientation]) + b"\0\0" + b"\0\0\0\0")
    segment = b"\xff\xe1" + (len(exif) + 2).to_bytes(2, "big") + exif
    return jpeg[:2] + segment + jpeg[2:]


@pytest.fixture(scope="session")
def jpeg() -> bytes:
    return encoded(letter(), "JPEG", quality=85)


@pytest.fixture(scope="session")
def png() -> bytes:
    return encoded(letter(mode="RGBA"), "PNG")


@pytest.fixture(scope="session")
def heic() -> bytes:
    return encoded(letter(), "HEIF", quality=80)


def reference_bind(pictures: list[tuple[str, bytes, bytes | None]], work: Path
                   ) -> tuple[bytes, list[dict[str, str]]]:
    """The same pictures bound by the reference library of medRDS: the PDF and what its
    origin names."""
    work.mkdir(parents=True, exist_ok=True)
    listed = []
    for n, (name, data, shown) in enumerate(pictures):
        (work / f"{n}.bin").write_bytes(data)
        if shown is not None:
            (work / f"{n}.shown").write_bytes(shown)
        listed.append({"name": name, "file": str(work / f"{n}.bin"),
                       "shown": str(work / f"{n}.shown") if shown is not None else None})
    script = (
        "import { readFileSync } from 'node:fs';"
        f"import {{ bindPictures }} from '{(MEDRDS / 'lib' / 'index.mjs').as_posix()}';"
        f"const listed = {json.dumps(listed)};"
        "const read = (file) => new Uint8Array(readFileSync(file));"
        "const pictures = listed.map((p) => ({ name: p.name, bytes: read(p.file),"
        " ...(p.shown ? { shown: read(p.shown) } : {}) }));"
        "const { bytes, bound } = await bindPictures(pictures);"
        "console.log(JSON.stringify({ pdf: Buffer.from(bytes).toString('base64'), bound }));")
    run = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True,
                         text=True, check=True)
    answer = json.loads(run.stdout)
    return base64.b64decode(answer["pdf"]), answer["bound"]


def reference_unbinds(pdf: Path) -> list[str]:
    """The SHA-256 of every picture the reference library takes out of a bound PDF."""
    script = (
        "import { readFileSync } from 'node:fs';"
        f"import {{ boundFiles, sha256 }} from '{(MEDRDS / 'lib' / 'index.mjs').as_posix()}';"
        f"const out = await boundFiles(new Uint8Array(readFileSync({json.dumps(str(pdf))})));"
        "console.log(JSON.stringify(await Promise.all(out.map((b) => b ? sha256(b) : null))));")
    run = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True,
                         text=True, check=True)
    return list(json.loads(run.stdout))
