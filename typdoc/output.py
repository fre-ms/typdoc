"""The files typdoc writes: the PDF and, beside it, the configuration document.

``<stem>.pdf`` is the bound PDF exactly as the standard has it; nothing of typdoc's is in
it.  ``<stem>.typdoc.json`` makes it again from the same pictures.
"""

from __future__ import annotations

from pathlib import Path

from doccor import documents

from typdoc.errors import TypdocError
from typdoc.project import SUFFIX, Bound


def write(bound: Bound, folder: str | Path, stem: str) -> dict[str, Path]:
    """Write the PDF and the configuration document into ``folder`` (made when missing);
    returns their paths by kind ("document": the bound PDF; "config").  Raises
    "unwritable"."""
    folder = Path(folder)
    paths = {"document": folder / f"{stem}.pdf", "config": folder / f"{stem}{SUFFIX}"}
    try:
        folder.mkdir(parents=True, exist_ok=True)
        paths["document"].write_bytes(bound.pdf)
        paths["config"].write_bytes(documents.document_bytes(bound.config))
    except OSError as e:
        raise TypdocError("unwritable") from e
    return paths
