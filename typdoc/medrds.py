"""Pictures bound into one PDF as the standard medRDS says (specification 9.5): the
writing side of its reference library (``lib/pdf.mjs``, ``bindPictures`` and ``jpegFacts``),
in Python, byte for byte.

Binding changes no picture.  A JPEG is the image of its page byte for byte; a picture of
another format is a file associated with its page (relationship ``Source``), byte for byte,
and the page shows a JPEG made of it.  Each page is turned as its picture's orientation
says (EXIF), by ``/Rotate``, and mirrored where the picture is.  A page's long side is
that of A4.  The PDF has no date, no identifier and nothing of the program that wrote it:
the same pictures give the same bytes, here and in the reference library, and the tests
let the reference library bind the same pictures and compare.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass

STANDARD = "0.15"  # the version of medRDS whose rule this is
LONG_SIDE = 842  # points: the long side of A4
_SOF = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
# how a page turns (clockwise, as /Rotate) and whether it is mirrored, by EXIF orientation
_TURN = {1: (0, False), 2: (0, True), 3: (180, False), 4: (180, True), 5: (270, True),
         6: (90, False), 7: (90, True), 8: (270, False)}
MEDIA_TYPES = {"png": "image/png", "heic": "image/heic", "heif": "image/heif",
               "tif": "image/tiff", "tiff": "image/tiff", "webp": "image/webp"}


class NotBound(ValueError):
    """What was given cannot be bound: no picture, no name, no JPEG to show."""


@dataclass(frozen=True)
class JpegFacts:
    """What a JPEG says of itself: its size in pixels, its colour components, its
    orientation (EXIF), whether Adobe inverted its CMYK."""

    width: int
    height: int
    components: int
    orientation: int = 1
    adobe: bool = False


@dataclass(frozen=True)
class Picture:
    """A picture to bind: its ``name`` (as the PDF and the origin name it), its ``data``
    as it came, and for a picture that is no JPEG the JPEG the page shows (``shown``)."""

    name: str
    data: bytes
    shown: bytes | None = None


def is_jpeg(data: bytes) -> bool:
    """True for what begins as a JPEG does."""
    return len(data) > 3 and data[0] == 0xFF and data[1] == 0xD8 and data[2] == 0xFF


def _exif_orientation(tiff: bytes) -> int | None:
    """The orientation tag (0x0112) of the first directory of an EXIF block, or None."""
    if len(tiff) < 8:
        return None
    little = tiff[0] == 0x49

    def number(at: int, length: int) -> int:
        return int.from_bytes(tiff[at:at + length], "little" if little else "big")

    def u16(at: int) -> int:
        return number(at, 2)

    directory = number(4, 4)
    if directory + 2 > len(tiff):
        return None
    for k in range(u16(directory)):
        entry = directory + 2 + k * 12
        if entry + 12 > len(tiff):
            return None
        if u16(entry) == 0x0112:
            value = u16(entry + 8)
            return value if 1 <= value <= 8 else None
    return None


def jpeg_facts(data: bytes) -> JpegFacts:
    """What a JPEG says of itself.  Raises :class:`NotBound` for what is no JPEG, a
    damaged one, or one that does not say its size and colours."""
    if not is_jpeg(data):
        raise NotBound("This is no JPEG.")
    width = height = components = 0
    orientation, adobe = 1, False
    i = 2
    while i + 4 <= len(data):
        if data[i] != 0xFF:
            raise NotBound("This JPEG is damaged.")
        while i < len(data) and data[i] == 0xFF:
            i += 1
        if i >= len(data):
            break
        marker = data[i]
        i += 1
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            continue
        if marker in (0xDA, 0xD9) or i + 2 > len(data):
            break
        length = (data[i] << 8) | data[i + 1]
        body = data[i + 2:i + length]
        if marker in _SOF and len(body) >= 6:
            height = (body[1] << 8) | body[2]
            width = (body[3] << 8) | body[4]
            components = body[5]
        elif marker == 0xE1 and body[:6] == b"Exif\0\0":
            orientation = _exif_orientation(body[6:]) or 1
        elif marker == 0xEE and body[:5] == b"Adobe":
            adobe = True
        i += length
    if not width or not height or components not in (1, 3, 4):
        raise NotBound("This JPEG does not say its size and colours.")
    return JpegFacts(width, height, components, orientation, adobe)


def _number(n: float) -> str:
    """A number as the reference library writes it: rounded to two places, without
    zeros that say nothing."""
    rounded = math.floor(n * 100 + 0.5) / 100
    return str(int(rounded)) if rounded == int(rounded) else repr(rounded)


def _pdf_text(text: str) -> str:
    """A text as a PDF string in UTF-16 with its byte order mark, in hexadecimal."""
    return "<FEFF" + text.encode("utf-16-be").hex().upper() + ">"


def _stream(dictionary: str, data: bytes) -> bytes:
    return f"<< {dictionary} /Length {len(data)} >>\nstream\n".encode() + data + b"\nendstream"


def bind(pictures: list[Picture]) -> tuple[bytes, list[dict[str, str]]]:
    """Several pictures of one document bound into one PDF, a page for each, in the order
    given.  Returns the PDF and, for the origin, each picture's name and SHA-256.  Raises
    :class:`NotBound`."""
    if not pictures:
        raise NotBound("There is no picture to bind.")
    objects: list[bytes | None] = []  # bodies, numbered from 1

    def add(body: bytes | None) -> int:
        objects.append(body)
        return len(objects)

    catalogue, pages = add(None), add(None)
    kids: list[int] = []
    attached: list[tuple[str, int]] = []  # name, number of its file specification
    bound: list[dict[str, str]] = []
    for k, picture in enumerate(pictures):
        if picture.name == "":
            raise NotBound(f"Picture {k + 1} has no name.")
        bound.append({"name": picture.name, "sha256": hashlib.sha256(picture.data).hexdigest()})
        jpeg = is_jpeg(picture.data)
        image = picture.data if jpeg else picture.shown
        if image is None or not is_jpeg(image):
            raise NotBound(f'"{picture.name}" is no JPEG, and nothing to show of it was '
                           "given as one.")
        facts = jpeg_facts(image)
        space = {1: "/DeviceGray", 3: "/DeviceRGB", 4: "/DeviceCMYK"}[facts.components]
        decode = " /Decode [1 0 1 0 1 0 1 0]" if facts.components == 4 and facts.adobe else ""
        image_number = add(_stream(
            f"/Type /XObject /Subtype /Image /Width {facts.width} /Height {facts.height} "
            f"/ColorSpace {space} /BitsPerComponent 8 /Filter /DCTDecode{decode}", image))
        scale = LONG_SIDE / max(facts.width, facts.height)
        w, h = facts.width * scale, facts.height * scale
        rotate, mirrored = _TURN[facts.orientation]
        matrix = (f"{_number(-w)} 0 0 {_number(h)} {_number(w)} 0" if mirrored
                  else f"{_number(w)} 0 0 {_number(h)} 0 0")
        content = add(_stream("", f"q {matrix} cm /Im0 Do Q".encode()))
        af = ""
        if not jpeg:
            name = picture.name
            ext = name[name.rfind(".") + 1:].lower() if "." in name else ""
            subtype = (f" /Subtype /{MEDIA_TYPES[ext].replace('/', '#2F')}"
                       if ext in MEDIA_TYPES else "")
            file_number = add(_stream(
                f"/Type /EmbeddedFile{subtype} /Params << /Size {len(picture.data)} >>",
                picture.data))
            spec = add(f"<< /Type /Filespec /F {_pdf_text(name)} /UF {_pdf_text(name)} "
                       f"/EF << /F {file_number} 0 R >> /AFRelationship /Source >>".encode())
            attached.append((name, spec))
            af = f" /AF [{spec} 0 R]"
        turn = f" /Rotate {rotate}" if rotate else ""
        kids.append(add(
            f"<< /Type /Page /Parent {pages} 0 R /MediaBox [0 0 {_number(w)} {_number(h)}]"
            f"{turn} /Resources << /XObject << /Im0 {image_number} 0 R >> >> "
            f"/Contents {content} 0 R{af} >>".encode()))
    names = ""
    if attached:
        listed = " ".join(f"{_pdf_text(n)} {number} 0 R" for n, number in attached)
        files = " ".join(f"{number} 0 R" for _n, number in attached)
        names = f" /Names << /EmbeddedFiles << /Names [{listed}] >> >> /AF [{files}]"
    objects[catalogue - 1] = f"<< /Type /Catalog /Pages {pages} 0 R{names} >>".encode()
    objects[pages - 1] = (f"<< /Type /Pages /Kids [{' '.join(f'{n} 0 R' for n in kids)}] "
                          f"/Count {len(kids)} >>").encode()
    # the header, and a comment of bytes above 127 that tells programs the file is binary
    parts = [b"%PDF-1.7\n", bytes([0x25, 0xE2, 0xE3, 0xCF, 0xD3, 0x0A])]
    length = sum(len(part) for part in parts)
    offsets: list[int] = []
    for k, body in enumerate(objects):
        assert body is not None
        offsets.append(length)
        part = f"{k + 1} 0 obj\n".encode() + body + b"\nendobj\n"
        parts.append(part)
        length += len(part)
    tail = f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    tail += "".join(f"{offset:010d} 00000 n \n" for offset in offsets)
    tail += (f"trailer\n<< /Size {len(objects) + 1} /Root {catalogue} 0 R >>\n"
             f"startxref\n{length}\n%%EOF\n")
    parts.append(tail.encode())
    return b"".join(parts), bound
