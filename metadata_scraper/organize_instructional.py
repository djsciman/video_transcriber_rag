"""Deprecated shim. Use `py -3 -m bjj_pipeline organize`."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from bjj_pipeline import organize_instructional as _impl

if __name__ != "__main__":
    sys.modules[__name__] = _impl
else:
    sys.stderr.write(
        "deprecated: organize_instructional.py is a shim; "
        "use `py -3 -m bjj_pipeline organize`\n"
    )
    raise SystemExit(_impl.main())
