# typdoc

typdoc changes a document's type and nothing else. A photo of a letter, a scanned page, several
pictures of one report become **one PDF**, bound as the standard
[medRDS](https://medrds.org) says (specification 9.5):

- a **JPEG** is the image of its page, byte for byte;
- a picture of **another format** (HEIC, PNG, TIFF, WebP …) is attached to its page as it came,
  byte for byte, and the page shows a JPEG made of it;
- each page is **turned as the picture's orientation says**, and is as long as a sheet of A4.

Binding changes no picture: every picture can be taken out of the PDF again exactly as it went in.
The PDF has no date and no identifier, so the same pictures in the same order give the same bytes,
here and in medRDS's reference library; the tests let that library bind the same pictures and
compare.

typdoc is one tool of [docrepro](https://github.com/fre-ms/docrepro), one tool for one step, each
usable on its own:

| order | tool | its step |
|---|---|---|
| 5 | **typdoc** | changes the type: binds pictures into a PDF |
| 10 | [optdoc](https://github.com/fre-ms/optdoc) | makes the page faithful |
| 20 | [ocrdoc](https://github.com/fre-ms/ocrdoc) | recognises areas, text, tables and barcodes |
| 30 | semdoc | understands the text (planned) |
| 40 | [tagdoc](https://github.com/fre-ms/tagdoc) | describes the document |
| 50 | attdoc | signs it (planned) |

**No step forces a file type.** PDF is the rule, since one file then holds the pages, their text,
a description and a signature; it is not a condition. typdoc is the one step that changes a
document's type, and it is optional: the steps after it take what they are handed, typdoc's PDF or
the picture as it came. Why the work is divided so: `docs/family-design.md` in optdoc.

**Status: pre-alpha (0.2.1).**

## Install

Python 3.12 or later, with [uv](https://docs.astral.sh/uv/):

```
git clone https://github.com/fre-ms/typdoc
cd typdoc
uv sync
```

## Command line

```
typdoc about
typdoc run photo.heic --out results/
typdoc run page-1.jpg page-2.jpg page-3.png --out results/
typdoc run page-1.jpg page-2.jpg page-3.png --out again/ --config results/page-1.typdoc.json
```

`run` binds the pictures in the order given and writes two files into the folder, named after the
first picture, and nothing anywhere else: `<name>.pdf`, the bound PDF exactly as the standard has
it (nothing of typdoc's is in it), and `<name>.typdoc.json`, the configuration document, from
which and the same pictures the same PDF is made again, byte for byte. Every command answers with
one JSON object on standard output, a failure too, with a fixed kind and its message in English
and German, and exit status 2. No answer quotes a document or its path.
[docs/interface.md](docs/interface.md) describes the answers and the configuration document.

In the PDF a picture is named by its place and its type (`picture-2.png`), never by the name of
its file, which may name a patient.

## In Python

```python
from typdoc import output
from typdoc.project import Project

project = Project.open(["page-1.jpg", "page-2.png"])
bound = project.build()
output.write(bound, "results", "letter")      # letter.pdf and letter.typdoc.json
```

`typdoc.medrds.bind(pictures)` is the binding of the standard itself.

## Not yet

- A file with several pictures in it (a TIFF of several pages) is refused (`several-frames`).
- Other directions (a PDF's pages as pictures) and other targets than PDF.

## Licence

GNU Affero General Public License 3.0 or later (see `LICENSE`).
