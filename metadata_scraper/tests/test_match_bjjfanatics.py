import csv
from pathlib import Path

import match_bjjfanatics


def _folder(root: Path, name: str) -> Path:
    path = root / name
    path.mkdir()
    return path


def _csv_rows(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8", newline="") as handle:
        return {
            str(Path(row["folder_path"]).resolve()): row["product_url"]
            for row in csv.DictReader(handle)
        }


def test_parser_takes_library_and_output_paths():
    args = match_bjjfanatics.build_parser().parse_args(
        ["--library", r"D:\instructionals", "--output", r"D:\matches.csv"]
    )
    assert args.library == Path(r"D:\instructionals")
    assert args.output == Path(r"D:\matches.csv")
    assert args.force is False


def test_existing_product_url_is_skipped(tmp_path: Path, capsys):
    library = tmp_path / "lib"
    library.mkdir()
    kept = _folder(library, "Half Guard Anthology by Lachlan Giles")
    missing = _folder(library, "New Wave Jiu Jitsu")
    output = tmp_path / "matches.csv"
    kept_url = "https://bjjfanatics.com/products/the-half-guard-anthology-by-lachlan-giles"
    output.write_text(
        f"folder_path,product_url\n{kept},{kept_url}\n",
        encoding="utf-8",
    )
    queries: list[str] = []

    def search(query: str):
        queries.append(query)
        return [
            {
                "title": "New Wave Jiu Jitsu by John Danaher",
                "handle": "new-wave-jiu-jitsu-by-john-danaher",
                "url": "/products/new-wave-jiu-jitsu-by-john-danaher",
            }
        ]

    code = match_bjjfanatics.main(
        ["--library", str(library), "--output", str(output)],
        search=search,
    )
    assert code == 0
    rows = _csv_rows(output)
    assert rows[str(kept.resolve())] == kept_url
    assert (
        rows[str(missing.resolve())]
        == "https://bjjfanatics.com/products/new-wave-jiu-jitsu-by-john-danaher"
    )
    assert all("Half Guard" not in query for query in queries)
    assert "skip" in capsys.readouterr().out.lower()


def test_force_researches_existing_product_url(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _folder(library, "Half Guard Anthology by Lachlan Giles")
    output = tmp_path / "matches.csv"
    output.write_text(
        "folder_path,product_url\n"
        f"{show},https://bjjfanatics.com/products/stale-listing\n",
        encoding="utf-8",
    )
    queries: list[str] = []

    def search(query: str):
        queries.append(query)
        return [
            {
                "title": "The Half Guard Anthology by Lachlan Giles",
                "handle": "the-half-guard-anthology-by-lachlan-giles",
                "url": "/products/the-half-guard-anthology-by-lachlan-giles",
            }
        ]

    code = match_bjjfanatics.main(
        ["--library", str(library), "--output", str(output), "--force"],
        search=search,
    )
    assert code == 0
    assert queries
    rows = _csv_rows(output)
    assert (
        rows[str(show.resolve())]
        == "https://bjjfanatics.com/products/the-half-guard-anthology-by-lachlan-giles"
    )


def test_prefers_instructional_over_bundle_listing(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _folder(library, "Half Guard Anthology by Lachlan Giles")
    output = tmp_path / "matches.csv"

    def search(query: str):
        return [
            {
                "title": "The Half Guard Anthology Bundle by Lachlan Giles",
                "handle": "the-half-guard-anthology-bundle-by-lachlan-giles",
                "url": "/products/the-half-guard-anthology-bundle-by-lachlan-giles",
            },
            {
                "title": "The Half Guard Anthology by Lachlan Giles",
                "handle": "the-half-guard-anthology-by-lachlan-giles",
                "url": "/products/the-half-guard-anthology-by-lachlan-giles",
            },
        ]

    code = match_bjjfanatics.main(
        ["--library", str(library), "--output", str(output)],
        search=search,
    )
    assert code == 0
    url = _csv_rows(output)[str(show.resolve())]
    assert url.endswith("/the-half-guard-anthology-by-lachlan-giles")
    assert "bundle" not in url


def test_default_walk_is_top_level_folders(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _folder(library, "Go Further Faster By John Danaher")
    (show / "Season 01").mkdir()
    (show / "Season 02").mkdir()
    output = tmp_path / "matches.csv"

    def search(query: str):
        return [
            {
                "title": "Go Further Faster by John Danaher",
                "handle": "go-further-faster-by-john-danaher",
                "url": "/products/go-further-faster-by-john-danaher",
            }
        ]

    code = match_bjjfanatics.main(
        ["--library", str(library), "--output", str(output)],
        search=search,
    )
    assert code == 0
    assert list(_csv_rows(output)) == [str(show.resolve())]
