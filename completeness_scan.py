"""Deprecated shim. Use `py -3 -m bjj_pipeline scan`."""

from __future__ import annotations

import sys

from bjj_pipeline import completeness_scan as _impl

if __name__ != "__main__":
    sys.modules[__name__] = _impl
else:
    sys.stderr.write(
        "deprecated: completeness_scan.py is a shim; use `py -3 -m bjj_pipeline scan`\n"
    )
    raise SystemExit(_impl.main())
