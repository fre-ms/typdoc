"""The command line: ``typdoc about`` and ``typdoc run``.

Every command answers with exactly one JSON object on standard output, whether it
succeeds or fails; a failure answers with its kind and its message in English and German,
and ends with exit status 2.  No answer and no message quotes a document or its path.
``--progress`` writes a line of JSON per picture to standard error.  The manners are
doccor's (:mod:`doccor.cli`): one JSON answer, standard error for its own lines, never the
network.  typdoc has no window: there is nothing to decide but the order of the pictures,
which is the order they are given in.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from doccor import cli as frame

from typdoc import __version__, medrds, pictures
from typdoc.errors import TypdocError
from typdoc.project import SUFFIX, TYPES, Options, Project, load_config

INTERFACE = 3  # the version of docs/interface.md the answers follow
TOOL = "typdoc"


def _about(args: argparse.Namespace) -> dict[str, Any]:
    """What typdoc binds, into what, and after which standard."""
    return {"version": __version__,
            "standard": f"https://medrds.org/spec/{medrds.STANDARD}",
            "pictures": [suffix.lstrip(".") for suffix in pictures.SUFFIXES],
            "to": list(TYPES)}


def _out(args: argparse.Namespace) -> Path:
    """The folder for the results: ``--out``, else ``<first picture>.typdoc`` beside it."""
    first = args.pictures[0]
    return args.out or first.with_name(f"{first.stem}.typdoc")


def _run(args: argparse.Namespace) -> dict[str, Any]:
    """Bind the pictures (or bind them again as their configuration document says) and
    write the results."""
    from typdoc import output

    if args.config is not None:
        if args.to is not None:  # the configuration document decides it
            raise TypdocError("usage")
        project = Project.open(args.pictures, config=load_config(args.config))
    else:
        project = Project.open(args.pictures, Options(to=args.to or TYPES[0]))
    bound = project.build(frame.progress if args.progress else None)
    paths = output.write(bound, _out(args), args.pictures[0].stem)
    return {**{k: str(v) for k, v in paths.items()}, "pages": bound.pages,
            "bound": [{"sha256": entry["sha256"], "attached": attached}
                      for entry, attached in zip(bound.bound, bound.attached, strict=True)]}


def _parser() -> argparse.ArgumentParser:
    """The argument parser."""
    p = frame.Parser(prog=TOOL, description="Change a document's type and nothing else: bind "
                                            "pictures into one PDF, each in it byte for byte.")
    p.add_argument("--version", action="version", version=f"{TOOL} {__version__}")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("about", help="what typdoc binds, and after which standard")
    ru = sub.add_parser("run", help="bind pictures into one PDF and write the results")
    ru.add_argument("pictures", type=Path, nargs="+",
                    help="the pictures of one document, in the order of its pages")
    ru.add_argument("--out", type=Path,
                    help="folder for the results (default: <first picture>.typdoc/)")
    ru.add_argument("--config", type=Path,
                    help="configuration to start from: <name>.typdoc.json")
    ru.add_argument("--to", choices=list(TYPES),
                    help="the type the document becomes (default and so far the only: pdf)")
    ru.add_argument("--progress", action="store_true",
                    help='a line {"page": n, "of": m} on standard error per picture')
    return p


COMMANDS: dict[str, Callable[[argparse.Namespace], dict[str, Any]]] = {
    "about": _about, "run": _run}


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line; returns the exit status."""
    return frame.main(_parser(), COMMANDS, tool=TOOL, version=__version__,
                      interface=INTERFACE, argv=argv)


__all__ = ["INTERFACE", "SUFFIX", "main"]
