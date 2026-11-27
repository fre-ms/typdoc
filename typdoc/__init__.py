"""typdoc: change a document's type and nothing else.

A photo, a scan, several pictures of one letter become one PDF, bound as the standard
medRDS says (specification 9.5): every picture is in it byte for byte, a JPEG as the image
of its page, a picture of another format attached to its page and shown as a JPEG.  typdoc
is step 5 of docrepro and optional there: the steps after it take what they are handed, a
PDF from typdoc or the picture as it came.

- :mod:`typdoc.medrds`: the binding of the standard, byte for byte as its reference
  library writes it.
- :mod:`typdoc.pictures`: reading a picture, and the JPEG a page shows of one that is none.
- :mod:`typdoc.project`: the pictures of one document and the configuration document
  (``<stem>.typdoc.json``) that makes the same PDF again.
- :mod:`typdoc.output`: the files written.
- :mod:`typdoc.cli`: ``typdoc about`` and ``typdoc run``.
"""

__version__ = "0.2.1"
