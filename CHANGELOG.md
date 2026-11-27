# Changelog

## 0.2.0 (2026-11-27)

Interface 2: one field renamed, in every tool of docrepro at once.

- **The answer names the bound PDF `document`**, no longer `pdf`; `typdoc.output.write` returns it
  under that key. The tools of docrepro name what they hand on alike, whatever its type. Callers
  read `document` where they read `pdf`.

## 0.1.0 (2026-11-27)

typdoc, step 5 of docrepro: a document's type changed, and nothing else.

- **The binding of the standard** (`typdoc.medrds`): pictures bound into one PDF as medRDS 9.5
  says. A JPEG is the image of its page byte for byte; a picture of another format is attached to
  its page (relationship `Source`) byte for byte and shown as a JPEG; each page is turned as its
  picture's orientation says; the long side is that of A4; no date, no identifier. The same
  bytes as medRDS's reference library writes: the tests let it bind the same pictures (JPEG, PNG,
  HEIC, TIFF; every orientation; grey and CMYK; odd sizes and names) and compare, and let it take
  the pictures out of typdoc's PDF again.
- **Pictures** (`typdoc.pictures`): JPEG, PNG, TIFF, HEIC and HEIF, WebP, BMP, GIF. What a page
  shows of a picture that is no JPEG is made upright, on white where it was transparent, in grey
  where it has no colour, at quality 92 with full colour resolution, without the picture's
  metadata.
- **The configuration document** `<stem>.typdoc.json`, format `typdoc-config` version 1: the
  pictures by their SHA-256 in the order of the pages. The same pictures and document give the
  same files, byte for byte. In the PDF a picture is named by its place and type, never by its
  file's name.
- **The command line**: `about` and `run`, one JSON answer whatever happens, kinds of error in
  English and German, never the network, nothing outside the results folder; interface 1
  (`docs/interface.md`). No window: there is nothing to decide but the order.
- **A step of docrepro** through the entry point `docrepro.steps`.
- Not yet: a file of several pictures (a TIFF of several pages) is refused (`several-frames`).
