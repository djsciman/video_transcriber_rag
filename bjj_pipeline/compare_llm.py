"""Copy user-specified corpus volumes and pare them with each chat vendor."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Sequence, TextIO

from .llm_metrics import (
    discover_volume_rels,
    metrics_from_dest,
    render_metrics_markdown,
)
from .prepare import (
    DEFAULT_LLM_PROVIDER,
    LLM_METHODS,
    LLM_PROVIDERS,
    Completer,
    _cleanup_spec,
    _extract_spec,
    make_completer,
    prepare_volume,
)

LLM_FIELDS = ("transcript_cleaned", "concepts", "suggested_tags", "techniques")
KEY_ENVS = tuple(cfg["key_env"] for cfg in LLM_PROVIDERS.values())
DEFAULT_PROVIDERS = "xai,openai,anthropic"


def strip_llm_fields(payload: dict) -> dict:
    copied = json.loads(json.dumps(payload))
    chapters = copied.get("chapters")
    if not isinstance(chapters, list):
        return copied
    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue
        for field in LLM_FIELDS:
            chapter.pop(field, None)
    return copied


def _volume_paths(corpus: Path, volumes: Sequence[str]) -> list[str]:
    rels: list[str] = []
    seen: set[str] = set()
    for raw in volumes:
        rel = raw.replace("\\", "/").strip()
        if not rel or rel in seen:
            continue
        seen.add(rel)
        rels.append(rel)
    return rels


def load_volume_list(
    volumes: Sequence[str] | None = None,
    volumes_file: Path | None = None,
) -> list[str]:
    found: list[str] = []
    if volumes:
        found.extend(volumes)
    if volumes_file is not None:
        text = Path(volumes_file).read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            found.append(stripped)
    return _volume_paths(Path("."), found)


def _key_status() -> list[tuple[str, bool]]:
    return [(name, bool(os.environ.get(name, "").strip())) for name in KEY_ENVS]


def _chapter_view(chapter: dict) -> dict:
    techniques = chapter.get("techniques")
    named = []
    if isinstance(techniques, list):
        for item in techniques:
            if isinstance(item, dict) and isinstance(item.get("named_move"), str):
                named.append(item["named_move"])
    cleaned = chapter.get("transcript_cleaned")
    return {
        "transcript_cleaned": cleaned if isinstance(cleaned, str) else None,
        "cleaned_chars": len(cleaned) if isinstance(cleaned, str) else 0,
        "concepts": chapter.get("concepts") if isinstance(chapter.get("concepts"), list) else [],
        "suggested_tags": (
            chapter.get("suggested_tags")
            if isinstance(chapter.get("suggested_tags"), list)
            else []
        ),
        "named_moves": named,
        "technique_count": len(techniques) if isinstance(techniques, list) else 0,
    }


def _print(stdout: TextIO, status: str, name: str, reason: str = "") -> None:
    line = f"{status:<4}  {'compare':<10}  {name}"
    if reason:
        line += f"  ({reason})"
    stdout.write(line + "\n")


def _chapter_slots(payload: dict, view_key: str) -> list[dict]:
    slots: list[dict] = []
    chapters = payload.get("chapters")
    if not isinstance(chapters, list):
        return slots
    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue
        slots.append({"title": chapter.get("title", ""), view_key: {}})
    return slots


def _fill_slots(slots: list[dict], payload: dict, view_key: str, label: str) -> None:
    chapters = payload.get("chapters")
    if not isinstance(chapters, list):
        return
    index = 0
    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue
        if index < len(slots):
            slots[index][view_key][label] = _chapter_view(chapter)
        index += 1


def _eligible_count(payload: dict) -> int:
    chapters = payload.get("chapters")
    if not isinstance(chapters, list):
        return 0
    n = 0
    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue
        raw = chapter.get("transcript_raw")
        if isinstance(raw, str) and raw.strip():
            n += 1
    return n


def _write_report(out: Path, report: dict, *, heading: str, view_key: str) -> None:
    _atomic_write(out / "report.json", json.dumps(report, indent=2) + "\n")
    lines = [heading, ""]
    for volume in report["volumes"]:
        lines.append(f"## {volume['path']}")
        lines.append("")
        for chapter in volume["chapters"]:
            lines.append(f"### {chapter['title']}")
            lines.append("")
            for label, view in (chapter.get(view_key) or {}).items():
                lines.append(f"- **{label}**")
                concepts = ", ".join(view.get("concepts") or []) or "(none)"
                tags = ", ".join(view.get("suggested_tags") or []) or "(none)"
                moves = ", ".join(view.get("named_moves") or []) or "(none)"
                lines.append(f"  - concepts: {concepts}")
                lines.append(f"  - suggested_tags: {tags}")
                lines.append(f"  - named_moves: {moves}")
                lines.append(f"  - technique_count: {view.get('technique_count', 0)}")
                lines.append(f"  - cleaned_chars: {view.get('cleaned_chars', 0)}")
            lines.append("")
    _atomic_write(out / "report.md", "\n".join(lines).rstrip() + "\n")


def _write_metrics(out: Path, volume_rels: Sequence[str], providers: Sequence[str]) -> None:
    metrics = metrics_from_dest(out, volume_rels, providers)
    _atomic_write(out / "metrics.json", json.dumps(metrics, indent=2) + "\n")
    _atomic_write(out / "metrics.md", render_metrics_markdown(metrics))


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def run(
    corpus: Path,
    out: Path,
    volumes: Sequence[str],
    *,
    library: Path | None = None,
    providers: Sequence[str] = ("xai", "openai", "anthropic"),
    models: dict[str, str] | None = None,
    methods: Sequence[str] | None = None,
    provider: str | None = None,
    model: str | None = None,
    max_chapters: int | None = None,
    dry_run: bool = False,
    completers: dict[str, Completer] | None = None,
    method_completers: dict[str, dict[str, Completer]] | None = None,
    stdout: TextIO | None = None,
) -> int:
    corpus = Path(corpus)
    out = Path(out)
    stdout = stdout if stdout is not None else sys.stdout
    models = models or {}
    rels = _volume_paths(corpus, volumes)
    if not rels:
        _print(stdout, "FAIL", "(none)", "no volumes specified")
        return 1

    for env_name, present in _key_status():
        _print(stdout, "KEY", env_name, "set" if present else "missing")

    failed = False
    payloads: dict[str, dict] = {}
    for rel in rels:
        src = corpus / rel
        if not src.is_file():
            _print(stdout, "FAIL", rel, "missing")
            failed = True
            continue
        payload = json.loads(src.read_text(encoding="utf-8"))
        payloads[rel] = payload
        n = _eligible_count(payload)
        budget = n if max_chapters is None else min(n, max_chapters)
        if methods:
            _print(
                stdout,
                "DRY" if dry_run else "PLAN",
                rel,
                f"{n} chapters, {budget} per method",
            )
        else:
            _print(stdout, "DRY" if dry_run else "PLAN", rel, f"{n} chapters, {budget} llm")

    if failed:
        return 1
    if dry_run:
        return 0

    method_mode = bool(methods)
    labels: list[str] = list(methods) if method_mode else list(providers)
    view_key = "by_method" if method_mode else "by_provider"
    heading = "# LLM method comparison" if method_mode else "# LLM provider comparison"
    sku_provider = provider or DEFAULT_LLM_PROVIDER
    sku_model = model
    if method_mode:
        sku_model = model or LLM_PROVIDERS[sku_provider]["model"]

    report: dict = {"volumes": []}
    for rel, payload in payloads.items():
        stripped = strip_llm_fields(payload)
        slots = _chapter_slots(stripped, view_key)
        source_bytes = (corpus / rel).read_bytes()
        for label in labels:
            dest = out / label / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(stripped, indent=2) + "\n", encoding="utf-8")
            llm_errors: list[str] = []

            def tracked(prompt: str, _completer: Completer) -> str:
                try:
                    return _completer(prompt)
                except Exception as exc:  # noqa: BLE001
                    llm_errors.append(str(exc))
                    raise

            try:
                if method_mode:
                    injected = (method_completers or {}).get(label, {})
                    chapter_budget = max_chapters
                    if label == "staged":
                        cleaner = injected.get("cleaner") or make_completer(
                            sku_provider,
                            sku_model,
                            spec=_cleanup_spec(),
                            reasoning_effort="low",
                        )
                        extractor = injected.get("extractor") or make_completer(
                            sku_provider,
                            sku_model,
                            spec=_extract_spec(),
                            reasoning_effort="medium",
                        )
                        call_budget = (
                            None if chapter_budget is None else chapter_budget * 2
                        )
                        code = prepare_volume(
                            dest,
                            out / label,
                            library,
                            cleaner=lambda prompt, _fn=cleaner: tracked(prompt, _fn),
                            extractor=lambda prompt, _fn=extractor: tracked(prompt, _fn),
                            force=True,
                            max_llm_calls=call_budget,
                        )
                    else:
                        one = injected.get("completer") or make_completer(
                            sku_provider, sku_model
                        )
                        code = prepare_volume(
                            dest,
                            out / label,
                            library,
                            completer=lambda prompt, _fn=one: tracked(prompt, _fn),
                            force=True,
                            max_llm_calls=chapter_budget,
                        )
                else:
                    if completers is not None and label in completers:
                        completer = completers[label]
                    else:
                        completer = make_completer(
                            label,
                            models.get(label) or LLM_PROVIDERS[label]["model"],
                        )
                    code = prepare_volume(
                        dest,
                        out / label,
                        library,
                        completer=lambda prompt, _fn=completer: tracked(prompt, _fn),
                        force=True,
                        max_llm_calls=max_chapters,
                    )
            except Exception as exc:  # noqa: BLE001
                _print(stdout, "FAIL", f"{label}/{rel}", str(exc))
                failed = True
                continue
            if code:
                reason = llm_errors[0] if llm_errors else "model half"
                _print(stdout, "FAIL", f"{label}/{rel}", reason)
                failed = True
            else:
                _print(stdout, "RUN", f"{label}/{rel}")
            result = json.loads(dest.read_text(encoding="utf-8"))
            _fill_slots(slots, result, view_key, label)
        if (corpus / rel).read_bytes() != source_bytes:
            _print(stdout, "FAIL", rel, "source mutated")
            failed = True
        report["volumes"].append({"path": rel, "chapters": slots})
    _write_report(out, report, heading=heading, view_key=view_key)
    _write_metrics(out, list(payloads), labels)
    return 1 if failed else 0


def refresh_from_existing(
    out: Path,
    providers: Sequence[str] = ("xai", "openai", "anthropic"),
    *,
    methods: Sequence[str] | None = None,
    stdout: TextIO | None = None,
) -> int:
    out = Path(out)
    stdout = stdout if stdout is not None else sys.stdout
    labels: list[str] = list(methods) if methods else list(providers)
    view_key = "by_method" if methods else "by_provider"
    heading = "# LLM method comparison" if methods else "# LLM provider comparison"
    rels = discover_volume_rels(out, labels)
    if not rels:
        _print(stdout, "FAIL", str(out), "no provider copies")
        return 1
    report: dict = {"volumes": []}
    for rel in rels:
        slots: list[dict] | None = None
        for label in labels:
            dest = out / label / rel
            if not dest.is_file():
                continue
            payload = json.loads(dest.read_text(encoding="utf-8"))
            if slots is None:
                slots = _chapter_slots(payload, view_key)
            _fill_slots(slots, payload, view_key, label)
        report["volumes"].append(
            {
                "path": rel,
                "chapters": slots or [],
            }
        )
        _print(stdout, "RUN", rel)
    _write_report(out, report, heading=heading, view_key=view_key)
    _write_metrics(out, rels, labels)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Copy user-specified corpus volumes into --out/<provider>/ and run "
            "--llm prepare for each vendor, or into --out/<method>/ for a "
            "one-call vs staged bake-off on one provider and model. The live "
            "corpus is not written."
        )
    )
    parser.add_argument("--corpus", type=Path, default=None, help="Live transcript corpus root.")
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Scratch directory for per-provider copies and the comparison report.",
    )
    parser.add_argument(
        "--library",
        type=Path,
        default=None,
        help="Optional video library root (tvshow.nfo instructor names).",
    )
    parser.add_argument(
        "--volume",
        action="append",
        default=[],
        dest="volumes",
        help="Corpus-relative JSON path. Repeat for a diverse sample.",
    )
    parser.add_argument(
        "--volumes-file",
        type=Path,
        default=None,
        help="Text file of corpus-relative JSON paths, one per line.",
    )
    parser.add_argument(
        "--providers",
        default=DEFAULT_PROVIDERS,
        help="Comma-separated vendors: xai, openai, anthropic.",
    )
    parser.add_argument(
        "--methods",
        default=None,
        help=(
            "Comma-separated prepare methods (one-call,staged). Writes "
            "--out/<method>/ under one --provider and --model. Separate from "
            "vendor-vs-vendor --providers."
        ),
    )
    parser.add_argument(
        "--provider",
        choices=sorted(LLM_PROVIDERS),
        default=None,
        help="Single vendor for --methods. Default: xai.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Single model id for --methods. Env: BJJ_LLM_MODEL.",
    )
    parser.add_argument(
        "--max-chapters",
        type=int,
        default=None,
        help=(
            "Chapter budget per volume, per provider or method. "
            "Staged spends two Completer calls per chapter."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the sample and which API keys are set; do not copy or call.",
    )
    parser.add_argument(
        "--from-existing",
        action="store_true",
        help="Rebuild report.md and metrics.md from --out copies; do not call the APIs.",
    )
    return parser


def _parse_csv_names(raw: str, allowed, flag: str) -> list[str]:
    kind = flag.lstrip("-")
    if kind.endswith("s"):
        kind = kind[:-1]
    display = ", ".join(sorted(allowed) if isinstance(allowed, dict) else allowed)
    names: list[str] = []
    for part in raw.split(","):
        name = part.strip().lower()
        if not name:
            continue
        if name not in allowed:
            raise SystemExit(
                f"error: unknown {kind} {name!r}; choose one of: {display}"
            )
        if name not in names:
            names.append(name)
    if not names:
        raise SystemExit(f"error: {flag} is empty")
    return names


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        rels = load_volume_list(args.volumes, args.volumes_file)
        if args.methods and args.providers != DEFAULT_PROVIDERS:
            raise SystemExit(
                "error: --methods cannot be combined with --providers; "
                "use --provider and --model"
            )
        providers = _parse_csv_names(args.providers, LLM_PROVIDERS, "--providers")
        methods = (
            _parse_csv_names(args.methods, LLM_METHODS, "--methods")
            if args.methods
            else None
        )
    except SystemExit as exc:
        if isinstance(exc.code, str):
            sys.stderr.write(exc.code + "\n")
            return 2
        raise
    if args.from_existing:
        return refresh_from_existing(args.out, providers=providers, methods=methods)
    if args.corpus is None:
        sys.stderr.write("error: --corpus is required unless --from-existing\n")
        return 2
    return run(
        args.corpus,
        args.out,
        rels,
        library=args.library,
        providers=providers,
        methods=methods,
        provider=args.provider or DEFAULT_LLM_PROVIDER,
        model=args.model,
        max_chapters=args.max_chapters,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
