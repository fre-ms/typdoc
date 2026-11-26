"""Reading a picture, and the JPEG a page shows of one that is no JPEG.

A JPEG is bound as it is.  Any other picture is attached to its page as it is, and the
page shows a JPEG made of it here: upright as its EXIF orientation says, in its colours (or
in grey where it has none), transparent parts on white, at quality 92 with full colour
resolution, without any of the picture's metadata.  The same picture gives the same JPEG
on the same version of typdoc.
"""

from __future__ import annotations

import io
from pathlib import Path

from typdoc import medrds
from typdoc.errors import TypdocError

SUFFIXES = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic", ".heif", ".webp", ".bmp", ".gif")
QUALITY = 92  # of the JPEG a page shows of a picture that is none


def read(path: Path) -> bytes:
    """The bytes of a picture file.  Raises "missing", "not-picture" (a PDF),
    "unsupported" (a type typdoc does not bind), "unreadable"."""
    if not path.is_file():
        raise TypdocError("missing")
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        raise TypdocError("not-picture")
    if suffix not in SUFFIXES:
        raise TypdocError("unsupported", suffix=suffix or "(none)")
    try:
        return path.read_bytes()
    except OSError as e:
        raise TypdocError("unreadable") from e


def shown(data: bytes) -> bytes | None:
    """The JPEG a page shows of a picture: None for a JPEG (it is shown as it is), else
    the JPEG made of it.  Raises "unreadable" for what is no picture, "several-frames"
    for a file of several."""
    if medrds.is_jpeg(data):
        try:
            medrds.jpeg_facts(data)
        except medrds.NotBound as e:
            raise TypdocError("unreadable") from e
        return None
    import pillow_heif
    from PIL import Image, ImageOps

    pillow_heif.register_heif_opener()
    try:
        with Image.open(io.BytesIO(data)) as image:
            if getattr(image, "n_frames", 1) > 1:
                raise TypdocError("several-frames")
            upright = ImageOps.exif_transpose(image)
            if upright.mode in ("RGBA", "LA", "PA") or "transparency" in upright.info:
                rgba = upright.convert("RGBA")
                white = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
                flat = Image.alpha_composite(white, rgba).convert("RGB")
            elif upright.mode in ("L", "1", "I;16", "I", "F"):
                flat = upright.convert("L")
            else:
                flat = upright.convert("RGB")
            buffer = io.BytesIO()
            flat.save(buffer, format="JPEG", quality=QUALITY, subsampling=0, optimize=False)
            return buffer.getvalue()
    except TypdocError:
        raise
    except Exception as e:  # Pillow words its failures with what it was given
        raise TypdocError("unreadable") from e
