"""Deprecated shim. Use `py -m bjj_pipeline transcribe`."""

from __future__ import annotations

import sys

from bjj_pipeline import batch_panoscribe as _impl

if __name__ != "__main__":
    sys.modules[__name__] = _impl
else:
    sys.stderr.write(
        "deprecated: batch_panoscribe.py is a shim; use `py -m bjj_pipeline transcribe`\n"
    )
    raise SystemExit(_impl.main())
