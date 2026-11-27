# typdoc's command line as an interface

**Interface 2**, since typdoc 0.2.0. This is what a program may rely on when it calls typdoc,
whatever language it is written in: a records app, a script, docrepro.

Every answer carries `interface`. It goes up when something a caller relies on changes in a way
that breaks it: a field or a kind of error removed or renamed, a meaning changed. Within one
interface, new fields, new options and new kinds of error may come; a caller ignores fields it
does not know and treats an unknown kind of error like any other (its message says what
happened). Releases are tagged; pin a tag, not a branch.

**From interface 1:** the answer names the bound PDF `document`, no longer `pdf`, as every tool of
docrepro does from now on (a document need not be a PDF, though typdoc's always is one).

typdoc does one step of docrepro: it **changes a document's type** and nothing else. Pictures
become one PDF, bound as the standard medRDS says (specification 9.5). The step is optional: the
steps after it take what they are handed, typdoc's PDF or the picture as it came.

## Calling

```
typdoc about
typdoc run <picture> [<picture> …] --out <folder> [--config <file.typdoc.json>] [--progress]
typdoc --version
```

Every command writes **exactly one JSON object to standard output**, whether it succeeds or not,
and ends with exit status **0** on success and **2** on failure. Standard error is free for
`--progress` and the usage line of an invalid command line. No answer and no message ever quotes
the content of a document or a path given to typdoc, since a file name may name a patient.
typdoc never goes on the network and writes nothing outside `<folder>`. It has no window: there
is nothing to decide but the order of the pictures, which is the order they are given in.

| field | example | meaning |
|---|---|---|
| `interface` | `2` | the version of this description |
| `made_with` | `"typdoc 0.2.0"` | the program and its version |

## `about`

```json
{"interface": 2, "made_with": "typdoc 0.2.0", "version": "0.2.0",
 "standard": "https://medrds.org/spec/0.15",
 "pictures": ["jpg", "jpeg", "png", "tif", "tiff", "heic", "heif", "webp", "bmp", "gif"],
 "to": ["pdf"]}
```

`standard` is the version of medRDS whose binding typdoc writes, `pictures` the file types it
binds, `to` the types a document can become (so far: PDF).

## `run`: bind pictures into one PDF

`<picture> …` are the pictures of one document, in the order of its pages. typdoc never changes
them. Into `<folder>` (made when missing; default `<first picture>.typdoc` beside the first
picture) it writes two files, named after the first picture:

| file | what it is |
|---|---|
| `<stem>.pdf` | the bound PDF, exactly as the standard has it: a page for each picture, nothing of typdoc's in it |
| `<stem>.typdoc.json` | the configuration document: from it and the same pictures, the same PDF again |

**The binding** (medRDS 9.5; the same bytes as the standard's reference library writes):

- A **JPEG** is the image of its page, byte for byte.
- A picture of **another format** is a file associated with its page (relationship `Source`),
  byte for byte, and the page shows a JPEG made of it: upright as the picture's EXIF orientation
  says, transparent parts on white, grey where the picture has no colour, at quality 92 with
  full colour resolution, with none of the picture's metadata.
- Each page is **turned as its picture's orientation says** (`/Rotate`; mirrored where the
  picture is), and its long side is that of A4 (842 points).
- The PDF has **no date, no identifier, no program's name**. Every picture can be taken out of
  it again as it went in.
- In the PDF a picture is named by its place and its type (`picture-2.png`), never by its
  file's name.

The answer:

```json
{"interface": 2, "made_with": "typdoc 0.2.0",
 "document": "<folder>/<stem>.pdf", "config": "<folder>/<stem>.typdoc.json", "pages": 2,
 "bound": [{"sha256": "…", "attached": false}, {"sha256": "…", "attached": true}]}
```

`bound` names every picture in the order of the pages by its SHA-256 and says whether it is
attached to its page (`true`: a picture that is no JPEG) or is the image of its page (`false`:
a JPEG). A records app that files the PDF names the pictures in its origin (medRDS 7.3,
`bound`) from this.

With `--config` typdoc binds as a configuration document says; `--to` beside it is a `usage`
error. With `--progress` a line `{"page": n, "of": m}` goes to standard error before each
picture.

## The configuration document: `typdoc-config`, version 1

```json
{"format": "typdoc-config", "version": 1, "made_with": "typdoc 0.2.0",
 "input": {"pictures": [{"sha256": "…", "bytes": 245678, "suffix": ".jpg"},
                        {"sha256": "…", "bytes": 1832011, "suffix": ".heic"}]},
 "options": {"to": "pdf"}}
```

The pictures by their SHA-256, in the order of the pages, and the type the document becomes; no
paths, no names, no times. For other pictures or another order the document is refused
(`config-mismatch`). **The same pictures and the same document give the same two files, byte for
byte**, on the same version of typdoc. The PDF does not carry the document (it is the standard's
PDF and nothing more); within docrepro the chain document does.

## Failures

```json
{"interface": 2, "made_with": "typdoc 0.2.0", "error": "not-picture", "details": {},
 "message": {"en": "typdoc binds pictures into a PDF; this file is a PDF already.",
             "de": "typdoc bindet Bilder zu einem PDF; diese Datei ist schon ein PDF."}}
```

| `error` | when | `details` |
|---|---|---|
| `missing` | a picture (or the configuration document) does not exist | |
| `not-picture` | a PDF was given: it is one already | |
| `unsupported` | a file type typdoc does not bind | `suffix` |
| `unreadable` | the file is no picture: damaged, or not what its name says | |
| `several-frames` | the file holds several pictures (a TIFF of several pages, an animation) | |
| `bad-config` | the document is no readable JSON, not of this version, or a value of the wrong kind | `reason`: `json`, `format`, `field` |
| `config-mismatch` | the document belongs to other pictures, or to another order | |
| `unwritable` | the folder cannot take the results | |
| `network` | something tried to reach the network; it was stopped | |
| `usage` | the command line is not valid (the usage line goes to standard error) | |
| `internal` | a fault of typdoc | `error`: the name of the exception class |

The same kinds and wording are there for programs that use typdoc as a Python library:
`typdoc.errors.TypdocError` (`kind`, `details`) and `typdoc.errors.describe_error(error, "de")`.

## Licence

typdoc is free software under the GNU Affero General Public License 3.0 or later; its source is at
https://github.com/fre-ms/typdoc.
