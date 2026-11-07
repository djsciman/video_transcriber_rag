"""py -3 -m bjj_pipeline match|organize|chapters|scan|transcribe|run"""

from __future__ import annotations

import importlib
import sys
from typing import Callable

from . import COMMANDS

_COMMAND_MODULES = {
    "match": "bjj_pipeline.match_bjjfanatics",
    "organize": "bjj_pipeline.organize_instructional",
    "chapters": "bjj_pipeline.generate_chapters",
    "scan": "bjj_pipeline.completeness_scan",
    "transcribe": "bjj_pipeline.batch_panoscribe",
    "run": "bjj_pipeline.run_pipeline",
}


def _status(exc: BaseException) -> int:
    code = getattr(exc, "code", 1)
    if code is None:
        return 0
    if isinstance(code, int):
        return code
    return 1


def _load_main(command: str) -> Callable[..., int | None]:
    module = importlib.import_module(_COMMAND_MODULES[command])
    return module.main


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    if not argv or argv[0] in {"-h", "--help"}:
        sys.stdout.write(
            "usage: py -3 -m bjj_pipeline "
            f"{{{ '|'.join(COMMANDS) }}} ...\n"
        )
        sys.stdout.write("\nSubcommands:\n")
        for name in COMMANDS:
            sys.stdout.write(f"  {name}\n")
        sys.stdout.write("\nPass --help after a subcommand for its flags.\n")
        return 0
    command = argv[0]
    if command not in _COMMAND_MODULES:
        sys.stderr.write(
            f"error: unknown command {command!r}. "
            f"Choose one of: {', '.join(COMMANDS)}\n"
        )
        return 2
    rest = argv[1:]
    try:
        result = _load_main(command)(rest)
    except SystemExit as exc:
        return _status(exc)
    return 0 if result is None else int(result)


if __name__ == "__main__":
    sys.exit(main())
