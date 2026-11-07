"""Deprecated shim. Use `py -m bjj_pipeline.find_color_frames`."""

from __future__ import annotations

import sys

from bjj_pipeline import find_color_frames as _impl

if __name__ != "__main__":
    sys.modules[__name__] = _impl
else:
    sys.stderr.write(
        "deprecated: find_color_frames.py is a shim; "
        "use `py -m bjj_pipeline.find_color_frames`\n"
    )
    raise SystemExit(_impl.main())
