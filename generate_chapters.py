"""Deprecated shim. Use `py -3 -m bjj_pipeline chapters`."""

from __future__ import annotations

import sys

from bjj_pipeline import generate_chapters as _impl

if __name__ != "__main__":
    sys.modules[__name__] = _impl
else:
    sys.stderr.write(
        "deprecated: generate_chapters.py is a shim; use `py -3 -m bjj_pipeline chapters`\n"
    )
    raise SystemExit(_impl.main())
