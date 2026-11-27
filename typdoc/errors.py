"""The errors typdoc reports: a fixed kind, the details its wording needs, and that
wording in English and German.  The kinds every tool of docrepro has, and those two tools
share, are worded alike (:mod:`doccor.errors`), so that one program can hold them all.  No
message quotes the content or the path of a document.
"""

from __future__ import annotations

from doccor import errors as _core
from doccor.errors import LANGUAGES, DocError, describe_error

_OWN: dict[str, dict[str, str]] = {
    "not-picture": {
        "en": "{tool} binds pictures into a PDF; this file is a PDF already.",
        "de": "{tool} bindet Bilder zu einem PDF; diese Datei ist schon ein PDF.",
    },
}

_core.register(_OWN)
KINDS = _core.KINDS
__all__ = ["KINDS", "LANGUAGES", "DocError", "TypdocError", "describe_error"]


class TypdocError(DocError):
    """An error typdoc can word for a person: its kind and the details the wording needs."""

    tool = "typdoc"
