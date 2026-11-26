"""typdoc as step 5 of docrepro, through the entry point ``docrepro.steps`` (see
docrepro's ``steps``): it takes the original where that is a picture and hands on a PDF.
docrepro does not import this module's types; it calls the methods its ``Adapter`` names.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import typdoc
from typdoc.project import Options, Project


class TypdocAdapter:
    """How docrepro works typdoc."""

    def __init__(self) -> None:
        self.version = typdoc.__version__

    def open(self, source: Path, config: dict[str, Any] | None, settings: dict[str, Any],
             scratch: Path) -> Project:
        """typdoc's project on the original picture."""
        return Project.open([source], None if config else Options(), config)

    def config(self, project: Project) -> dict[str, Any]:
        return project.config()

    def write(self, project: Project, folder: Path, stem: str,
              progress: Callable[[int, int], None] | None) -> dict[str, Path]:
        from typdoc import output

        return output.write(project.build(progress), folder, stem)

    def dropped(self, project: Project) -> list[int]:
        return []  # typdoc always starts from the pictures

    def close(self, project: Project) -> None:
        project.close()
