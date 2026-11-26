"""The pictures of one document, bound into one PDF, and the configuration document that
makes the same PDF again.

typdoc has nothing to decide but the order of the pictures, which is the order they are
given in.  Its configuration document (``<stem>.typdoc.json``, format ``typdoc-config``)
names every picture by its SHA-256, in that order, and the type the document becomes;
no paths, no names, no times.  The same pictures in the same order give the same PDF,
byte for byte: the binding of the standard (:mod:`typdoc.medrds`) writes no date and no
identifier.

In the PDF a picture is named by its place and its type (``picture-1.heic``), never by
the name of its file, which may name a patient.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from doccor import documents
from doccor.errors import DocError

from typdoc import __version__, medrds, pictures
from typdoc.errors import TypdocError

FORMAT = "typdoc-config"
FORMAT_VERSION = 1
SUFFIX = ".typdoc.json"
TYPES = ("pdf",)  # the types a document can become

Progress = Callable[[int, int], None]  # picture (from 1) about to be bound, and how many


def load_config(path: str | Path) -> dict[str, Any]:
    """A configuration document from its file.  Raises "missing", or "bad-config" (reason
    "json" or "format"); the PDF typdoc writes is the standard's bound PDF and carries
    none."""
    try:
        return documents.load_document(path, FORMAT, FORMAT_VERSION, "typdoc.json", "typdoc")
    except DocError as e:
        reason = e.details.get("reason")
        raise (TypdocError(e.kind, reason=reason) if reason is not None
               else TypdocError(e.kind)) from e


@dataclass(frozen=True)
class Options:
    """The settings: the type the document becomes (``to``; "pdf")."""

    to: str = "pdf"

    @classmethod
    def from_dict(cls, data: Any) -> Options:
        if not isinstance(data, dict) or data.get("to") not in TYPES:
            raise TypdocError("bad-config", reason="field")
        return cls(to=data["to"])


@dataclass(frozen=True)
class Bound:
    """The result: the PDF's bytes, what the origin names of every picture (``bound``: its
    name in the PDF and its SHA-256), and for every picture whether it is attached to
    its page (a picture that is no JPEG) or is the image of its page (a JPEG)."""

    pdf: bytes
    bound: list[dict[str, str]]
    attached: list[bool]
    config: dict[str, Any]


class Project:
    """The pictures of one document, in their order."""

    def __init__(self, files: list[tuple[str, bytes]], options: Options) -> None:
        self.files = files  # suffix (lower case, with its dot) and bytes of every picture
        self.options = options

    @classmethod
    def open(cls, paths: Sequence[str | Path], options: Options | None = None,
             config: dict[str, Any] | None = None) -> Project:
        """The project on the pictures given, in that order; fresh, or as a configuration
        document says (whose settings then count).  Raises what reading a picture raises
        (:func:`typdoc.pictures.read`), "usage" for no picture at all, "config-mismatch"
        when the document belongs to other pictures or another order, "bad-config"."""
        if not paths:
            raise TypdocError("usage")
        files = [(Path(p).suffix.lower(), pictures.read(Path(p))) for p in paths]
        if config is None:
            return cls(files, options or Options())
        named = config.get("input")
        listed = named.get("pictures") if isinstance(named, dict) else None
        if not isinstance(listed, list) or not all(isinstance(entry, dict) for entry in listed):
            raise TypdocError("bad-config", reason="field")
        if [entry.get("sha256") for entry in listed] != [_sha256(data) for _s, data in files]:
            raise TypdocError("config-mismatch")
        return cls(files, Options.from_dict(config.get("options")))

    def config(self) -> dict[str, Any]:
        """The configuration document: the pictures by their SHA-256 in their order, and
        the settings."""
        return {"format": FORMAT, "version": FORMAT_VERSION, "made_with": f"typdoc {__version__}",
                "input": {"pictures": [{"sha256": _sha256(data), "bytes": len(data),
                                        "suffix": suffix} for suffix, data in self.files]},
                "options": {"to": self.options.to}}

    def build(self, progress: Progress | None = None) -> Bound:
        """Bind the pictures.  Raises "unreadable" for what is no picture, and
        "several-frames"."""
        bound_pictures: list[medrds.Picture] = []
        for n, (suffix, data) in enumerate(self.files, 1):
            if progress is not None:
                progress(n, len(self.files))
            bound_pictures.append(medrds.Picture(f"picture-{n}{suffix}", data,
                                                 pictures.shown(data)))
        try:
            pdf, bound = medrds.bind(bound_pictures)
        except medrds.NotBound as e:
            raise TypdocError("unreadable") from e
        return Bound(pdf, bound, [p.shown is not None for p in bound_pictures], self.config())

    def close(self) -> None:
        """Nothing is held open; here for the manners of the other tools' projects."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
