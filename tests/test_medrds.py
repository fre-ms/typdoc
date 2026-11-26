"""The binding of the standard: what a JPEG says of itself, pages turned as the pictures
say, every picture in the PDF as it came, and the same bytes as the reference library of
medRDS writes for the same pictures."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pymupdf
import pytest

from tests.conftest import (
    MEDRDS,
    encoded,
    letter,
    needs_medrds,
    reference_bind,
    reference_unbinds,
    with_orientation,
)
from typdoc import medrds, pictures


def test_what_a_jpeg_says_of_itself(jpeg: bytes) -> None:
    assert medrds.jpeg_facts(jpeg) == medrds.JpegFacts(420, 594, 3, 1, False)
    assert medrds.jpeg_facts(with_orientation(jpeg, 6)).orientation == 6
    grey = encoded(letter(mode="L"), "JPEG")
    assert medrds.jpeg_facts(grey).components == 1
    cmyk = encoded(letter().convert("CMYK"), "JPEG")
    assert medrds.jpeg_facts(cmyk) == medrds.JpegFacts(420, 594, 4, 1, True)
    for broken in (b"no picture", jpeg[:2] + b"\x00\x00" + jpeg[2:], b"\xff\xd8\xff\xd9"):
        with pytest.raises(medrds.NotBound):
            medrds.jpeg_facts(broken)


def test_pages_stand_the_right_way_up(jpeg: bytes) -> None:
    """Turned as the picture says, mirrored where it is; the long side that of A4."""
    def page(orientation: int) -> str:
        pdf, _bound = medrds.bind([medrds.Picture("a.jpeg", with_orientation(jpeg, orientation))])
        return pdf.decode("latin-1")

    assert "/Rotate" not in page(1) and "/MediaBox [0 0 595.35 842]" in page(1)
    assert "/Rotate 90" in page(6) and "/Rotate 180" in page(3) and "/Rotate 270" in page(8)
    assert "q -595.35 0 0 842 595.35 0 cm" in page(2)
    assert "/Rotate 90" in page(7) and "q -595.35 0 0 842 595.35 0 cm" in page(7)
    assert "/Rotate 270" in page(5) and "/Rotate 180" in page(4)
    with pytest.raises(medrds.NotBound):
        medrds.bind([])
    with pytest.raises(medrds.NotBound):
        medrds.bind([medrds.Picture("a.png", b"no jpeg")])
    with pytest.raises(medrds.NotBound):
        medrds.bind([medrds.Picture("", jpeg)])


def test_every_picture_is_in_the_pdf_as_it_came(tmp_path: Path, jpeg: bytes, png: bytes,
                                                heic: bytes) -> None:
    """A JPEG is the image of its page byte for byte; a picture of another format is
    attached to its page, byte for byte, and its page shows a JPEG."""
    given = [medrds.Picture("picture-1.jpg", jpeg),
             medrds.Picture("picture-2.png", png, pictures.shown(png)),
             medrds.Picture("picture-3.heic", heic, pictures.shown(heic))]
    pdf, bound = medrds.bind(given)
    assert bound == [{"name": p.name, "sha256": hashlib.sha256(p.data).hexdigest()}
                     for p in given]
    assert pdf.startswith(b"%PDF-1.7\n") and jpeg in pdf and png in pdf and heic in pdf
    path = tmp_path / "bound.pdf"
    path.write_bytes(pdf)
    with pymupdf.open(path) as doc:
        assert len(doc) == 3 and all(page.rect.height == 842 for page in doc)
        assert sorted(doc.embfile_names()) == ["picture-2.png", "picture-3.heic"]
        assert doc.embfile_get("picture-2.png") == png
        assert doc.embfile_get("picture-3.heic") == heic
        for page in doc:  # each page shows its picture: the letter's frame is on it
            pix = page.get_pixmap(dpi=50)
            assert pix.width > 300 and min(pix.samples) < 80
    text = pdf.decode("latin-1")
    assert text.count("/AFRelationship /Source") == 2
    assert "/Subtype /image#2Fpng" in text and "/Subtype /image#2Fheic" in text
    assert b"/Info" not in pdf and b"/ID" not in pdf and b"typdoc" not in pdf
    assert medrds.bind(given)[0] == pdf  # the same pictures, the same bytes


@needs_medrds
def test_the_same_bytes_as_the_reference_library(tmp_path: Path, jpeg: bytes, png: bytes,
                                                 heic: bytes) -> None:
    """medRDS's own library binds the same pictures: the PDFs are the same, byte for
    byte, whatever the pictures' formats, orientations, colours and names; and it takes
    out of typdoc's PDF every picture as it went in."""
    assert medrds.STANDARD in (MEDRDS / "schema" / "medrds.json").read_text(encoding="utf-8")[:200]
    cases: list[list[tuple[str, bytes, bytes | None]]] = [
        [("picture-1.jpg", jpeg, None)],
        [("IMG_1.jpeg", jpeg, None), ("Seite 2 – Anlage.png", png, pictures.shown(png)),
         ("picture-3.heic", heic, pictures.shown(heic))],
        [(f"turned-{n}.jpg", with_orientation(jpeg, n), None) for n in range(1, 9)],
        [("grey.jpg", encoded(letter(mode="L"), "JPEG"), None),
         ("cmyk.jpg", encoded(letter().convert("CMYK"), "JPEG"), None),
         ("wide.jpg", encoded(letter(900, 300), "JPEG"), None),
         ("odd.jpg", encoded(letter(333, 517), "JPEG"), None),
         ("scan.tiff", encoded(letter(mode="L"), "TIFF"),
          pictures.shown(encoded(letter(mode="L"), "TIFF"))),
         ("ohne-endung", png, pictures.shown(png))],
    ]
    for k, case in enumerate(cases):
        ours, bound = medrds.bind([medrds.Picture(*picture) for picture in case])
        theirs, their_bound = reference_bind(case, tmp_path / str(k))
        assert bound == their_bound, k
        assert ours == theirs, k
        path = tmp_path / f"{k}.pdf"
        path.write_bytes(ours)
        assert reference_unbinds(path) == [entry["sha256"] for entry in bound], k
