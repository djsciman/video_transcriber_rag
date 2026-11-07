"""Deprecated shim. Use `py -3 -m bjj_pipeline match`."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from bjj_pipeline import match_bjjfanatics as _impl

if __name__ != "__main__":
    sys.modules[__name__] = _impl
else:
    sys.stderr.write(
        "deprecated: match_bjjfanatics.py is a shim; use `py -3 -m bjj_pipeline match`\n"
    )
    raise SystemExit(_impl.main())
