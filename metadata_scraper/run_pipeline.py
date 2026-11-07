"""Deprecated shim. Use `py -m bjj_pipeline run`."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from bjj_pipeline import run_pipeline as _impl

if __name__ != "__main__":
    sys.modules[__name__] = _impl
else:
    sys.stderr.write(
        "deprecated: run_pipeline.py is a shim; use `py -m bjj_pipeline run`\n"
    )
    raise SystemExit(_impl.main())
