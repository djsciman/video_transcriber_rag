"""Package subcommands, extras, and one-cycle shims."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SUBCOMMANDS = ("match", "organize", "chapters", "scan", "transcribe", "run")

SHIMS = (
    (REPO / "generate_chapters.py", "chapters"),
    (REPO / "find_color_frames.py", "find_color_frames"),
    (REPO / "batch_panoscribe.py", "transcribe"),
    (REPO / "completeness_scan.py", "scan"),
    (REPO / "metadata_scraper" / "organize_instructional.py", "organize"),
    (REPO / "metadata_scraper" / "match_bjjfanatics.py", "match"),
    (REPO / "metadata_scraper" / "run_pipeline.py", "run"),
)


def _module(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "bjj_pipeline", *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )


def test_run_help_lists_library_and_corpus():
    proc = _module("run", "--help")
    assert proc.returncode == 0
    assert "--library" in proc.stdout
    assert "--corpus" in proc.stdout


@pytest.mark.parametrize("command", SUBCOMMANDS)
def test_subcommand_help_exits_0(command: str):
    proc = _module(command, "--help")
    assert proc.returncode == 0
    assert proc.stdout


def test_package_help_lists_subcommands():
    proc = _module("--help")
    assert proc.returncode == 0
    assert "py -3 -m bjj_pipeline" in proc.stdout
    for command in SUBCOMMANDS:
        assert command in proc.stdout


@pytest.mark.parametrize("path,command", SHIMS)
def test_old_script_prints_deprecation_and_still_helps(path: Path, command: str):
    proc = subprocess.run(
        [sys.executable, str(path), "--help"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "deprecated" in proc.stderr.lower()
    assert "py -3 -m bjj_pipeline" in proc.stderr
    assert proc.stdout


def test_no_split_bundles_shim():
    assert not (REPO / "metadata_scraper" / "split_bundles.py").exists()
    assert not (REPO / "split_bundles.py").exists()


def test_readme_operator_path_lists_prepare():
    text = (REPO / "README.md").read_text(encoding="utf-8")
    assert "Default stages are **match, organize, detect, transcribe, prepare**." in text
    assert "Apply match, organize, detect, transcribe, and prepare." in text
    assert "`--force-stage match\\|organize\\|detect\\|transcribe\\|prepare`" in text
    assert "| prepare | Every real chapter" in text
    assert "`transcript_cleaned`" in text
    assert "`BJJ_LLM_BASE_URL`" in text
    assert "`http://localhost:11434/v1`" in text
    assert "`BJJ_LLM_MODEL`" in text
    assert "`qwen3.5:4b`" in text
    assert "Ollama" in text
    assert "in place" in text
    assert "`segments`" in text


def test_pyproject_declares_organize_transcribe_all_extras():
    data = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    extras = data["project"]["optional-dependencies"]
    organize = " ".join(extras["organize"]).lower()
    transcribe = " ".join(extras["transcribe"]).lower()
    assert "beautifulsoup4" in organize
    assert "lxml" in organize
    assert "pytest" not in organize
    transcribe_need = ("numpy", "opencv", "rapidocr", "panoscribe")
    for name in transcribe_need:
        assert name in transcribe
    assert "all" in extras
    joined_all = " ".join(extras["all"]).lower()
    assert "organize" in joined_all and "transcribe" in joined_all
