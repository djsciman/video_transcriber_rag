"""Extracted index of unreviewed techniques, approved techniques, and concepts."""

from __future__ import annotations

import array
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

HOP_FIELDS = (
    "named_move",
    "ruleset",
    "move_type",
    "start_occupancy",
    "start_position",
    "end_occupancy",
    "end_position",
)
WRITABLE_FIELDS = HOP_FIELDS + ("technique_steps", "main_ideas")


@dataclass(frozen=True)
class ExtractedRow:
    video_file: str
    chapter_title: str
    chapter_start: float
    kind: str
    array_index: int
    status: str = ""
    named_move: str = ""
    ruleset: str = ""
    move_type: str = ""
    start_occupancy: str = ""
    start_position: str = ""
    end_occupancy: str = ""
    end_position: str = ""
    technique_steps: str = ""
    main_ideas: str = ""
    concept: str = ""
    instructor: str = ""
    instructional: str = ""
    extract: dict | None = None


class ExtractedIndex:
    """Local SQLite store of raw techniques and concepts. Sibling of CuratedStore."""

    def __init__(self, *, embedder=None, chat=None) -> None:
        self._embedder = embedder
        self._chat = chat
        self._conn = sqlite3.connect(":memory:")
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    @classmethod
    def open(cls, location, *, embedder=None, chat=None) -> ExtractedIndex:
        index = cls.__new__(cls)
        index._embedder = embedder
        index._chat = chat
        path = Path(location)
        path.parent.mkdir(parents=True, exist_ok=True)
        index._conn = sqlite3.connect(str(path))
        index._conn.row_factory = sqlite3.Row
        index._init_schema()
        return index

    def ingest_chapter(self, volume, chapter, corpus_json_path=None) -> None:
        video_file = volume.get("video_file") if isinstance(volume, dict) else ""
        if not isinstance(video_file, str):
            video_file = ""
        instructor = ""
        instructional = ""
        if isinstance(volume, dict):
            instructor = volume.get("instructor") or ""
            instructional = volume.get("instructional") or ""
        if isinstance(chapter, dict):
            if not instructor:
                instructor = chapter.get("instructor") or ""
            if not instructional:
                instructional = chapter.get("instructional") or ""
        instructor = instructor if isinstance(instructor, str) else ""
        instructional = instructional if isinstance(instructional, str) else ""
        title = chapter.get("title") if isinstance(chapter, dict) else ""
        if not isinstance(title, str):
            title = ""
        start = chapter.get("start") if isinstance(chapter, dict) else 0.0
        try:
            chapter_start = float(start)
        except (TypeError, ValueError):
            chapter_start = 0.0
        json_path = "" if corpus_json_path is None else str(corpus_json_path)
        self._clear_unreviewed_for_chapter(video_file, title, chapter_start)

        techniques = chapter.get("techniques") if isinstance(chapter, dict) else None
        if isinstance(techniques, list):
            for array_index, item in enumerate(techniques):
                if not isinstance(item, dict):
                    continue
                if self._reviewed_technique_exists(
                    video_file, title, chapter_start, array_index
                ):
                    continue
                extract = dict(item)
                hops = {
                    field: item[field] if isinstance(item.get(field), str) else ""
                    for field in HOP_FIELDS
                }
                steps = item.get("technique_steps") if isinstance(item.get("technique_steps"), str) else ""
                ideas = item.get("main_ideas") if isinstance(item.get("main_ideas"), str) else ""
                embedding = self._embedding_blob(
                    self._technique_embed_text(hops["named_move"], steps, ideas)
                )
                self._upsert(
                    video_file=video_file,
                    chapter_title=title,
                    chapter_start=chapter_start,
                    kind="technique",
                    array_index=array_index,
                    status="unreviewed",
                    hops=hops,
                    technique_steps=steps,
                    main_ideas=ideas,
                    concept="",
                    instructor=instructor,
                    instructional=instructional,
                    extract=extract,
                    corpus_json_path=json_path,
                    embedding=embedding,
                )

        concepts = chapter.get("concepts") if isinstance(chapter, dict) else None
        if isinstance(concepts, list):
            for array_index, item in enumerate(concepts):
                if not isinstance(item, str):
                    continue
                empty_hops = {field: "" for field in HOP_FIELDS}
                embedding = self._embedding_blob(item)
                self._upsert(
                    video_file=video_file,
                    chapter_title=title,
                    chapter_start=chapter_start,
                    kind="concept",
                    array_index=array_index,
                    status="",
                    hops=empty_hops,
                    technique_steps="",
                    main_ideas="",
                    concept=item,
                    instructor=instructor,
                    instructional=instructional,
                    extract={"concept": item},
                    corpus_json_path=json_path,
                    embedding=embedding,
                )

    def rows(self) -> tuple[ExtractedRow, ...]:
        cursor = self._conn.execute(
            """
            SELECT video_file, chapter_title, chapter_start, kind, array_index,
                   status, named_move, ruleset, move_type, start_occupancy,
                   start_position, end_occupancy, end_position, technique_steps,
                   main_ideas, concept, instructor, instructional, extract_json
            FROM extract
            ORDER BY video_file, chapter_start, kind, array_index
            """
        )
        return tuple(self._row_from_sql(row) for row in cursor)

    def save(self, row, fields, *, write_back_corpus=False) -> None:
        self._write_finder(row, fields, accept=False, write_back_corpus=write_back_corpus)

    def save_and_accept(self, row, fields, *, write_back_corpus=False) -> None:
        self._write_finder(row, fields, accept=True, write_back_corpus=write_back_corpus)

    def accept(self, row, *, write_back_corpus=False) -> None:
        self._write_finder(row, {}, accept=True, write_back_corpus=write_back_corpus)

    def save_many(self, rows, fields, *, write_back_corpus=False) -> None:
        for item in rows:
            self.save(item, fields, write_back_corpus=write_back_corpus)

    def save_and_accept_many(self, rows, fields, *, write_back_corpus=False) -> None:
        for item in rows:
            self.save_and_accept(item, fields, write_back_corpus=write_back_corpus)

    def close(self) -> None:
        self._conn.close()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS extract (
                video_file TEXT NOT NULL,
                chapter_title TEXT NOT NULL,
                chapter_start REAL NOT NULL,
                kind TEXT NOT NULL,
                array_index INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT '',
                named_move TEXT NOT NULL DEFAULT '',
                ruleset TEXT NOT NULL DEFAULT '',
                move_type TEXT NOT NULL DEFAULT '',
                start_occupancy TEXT NOT NULL DEFAULT '',
                start_position TEXT NOT NULL DEFAULT '',
                end_occupancy TEXT NOT NULL DEFAULT '',
                end_position TEXT NOT NULL DEFAULT '',
                named_move_stripped TEXT NOT NULL DEFAULT '',
                ruleset_stripped TEXT NOT NULL DEFAULT '',
                move_type_stripped TEXT NOT NULL DEFAULT '',
                start_occupancy_stripped TEXT NOT NULL DEFAULT '',
                start_position_stripped TEXT NOT NULL DEFAULT '',
                end_occupancy_stripped TEXT NOT NULL DEFAULT '',
                end_position_stripped TEXT NOT NULL DEFAULT '',
                technique_steps TEXT NOT NULL DEFAULT '',
                main_ideas TEXT NOT NULL DEFAULT '',
                suggested_tags TEXT NOT NULL DEFAULT '[]',
                source_time_ranges TEXT NOT NULL DEFAULT '[]',
                concept TEXT NOT NULL DEFAULT '',
                instructor TEXT NOT NULL DEFAULT '',
                instructional TEXT NOT NULL DEFAULT '',
                transcript_folder TEXT NOT NULL DEFAULT '',
                corpus_json_path TEXT NOT NULL DEFAULT '',
                extract_json TEXT NOT NULL DEFAULT '{}',
                embedding BLOB,
                PRIMARY KEY (video_file, chapter_title, chapter_start, kind, array_index)
            )
            """
        )
        self._conn.commit()

    def _clear_unreviewed_for_chapter(
        self, video_file: str, chapter_title: str, chapter_start: float
    ) -> None:
        self._conn.execute(
            """
            DELETE FROM extract
            WHERE video_file = ?
              AND chapter_title = ?
              AND chapter_start = ?
              AND NOT (kind = 'technique' AND status = 'reviewed')
            """,
            (video_file, chapter_title, chapter_start),
        )
        self._conn.commit()

    def _reviewed_technique_exists(
        self,
        video_file: str,
        chapter_title: str,
        chapter_start: float,
        array_index: int,
    ) -> bool:
        found = self._conn.execute(
            """
            SELECT 1 FROM extract
            WHERE video_file = ?
              AND chapter_title = ?
              AND chapter_start = ?
              AND kind = 'technique'
              AND array_index = ?
              AND status = 'reviewed'
            """,
            (video_file, chapter_title, chapter_start, array_index),
        ).fetchone()
        return found is not None

    def _write_finder(self, row, fields, *, accept: bool, write_back_corpus: bool) -> None:
        current = self._load_sql(row)
        if accept and current["kind"] == "concept":
            raise ValueError("Concept rows cannot be accepted")
        hops = {field: current[field] for field in HOP_FIELDS}
        steps = current["technique_steps"]
        ideas = current["main_ideas"]
        extract = json.loads(current["extract_json"] or "{}")
        if not isinstance(extract, dict):
            extract = {}
        for name, value in (fields or {}).items():
            if name not in WRITABLE_FIELDS:
                continue
            text = value if isinstance(value, str) else ""
            if name in HOP_FIELDS:
                hops[name] = text
            elif name == "technique_steps":
                steps = text
            else:
                ideas = text
            extract[name] = text
        if accept:
            hops = {field: hops[field].rstrip("*") for field in HOP_FIELDS}
            for field in HOP_FIELDS:
                stored = extract.get(field)
                if isinstance(stored, str):
                    extract[field] = stored.rstrip("*")
        old_text = self._technique_embed_text(
            current["named_move"], current["technique_steps"], current["main_ideas"]
        )
        new_text = self._technique_embed_text(hops["named_move"], steps, ideas)
        embedding = current["embedding"]
        if new_text != old_text:
            embedding = self._embedding_blob(new_text)
        stripped = {field: hops[field].rstrip("*") for field in HOP_FIELDS}
        status = "reviewed" if accept else current["status"]
        self._conn.execute(
            """
            UPDATE extract SET
                status = ?,
                named_move = ?, ruleset = ?, move_type = ?, start_occupancy = ?,
                start_position = ?, end_occupancy = ?, end_position = ?,
                named_move_stripped = ?, ruleset_stripped = ?, move_type_stripped = ?,
                start_occupancy_stripped = ?, start_position_stripped = ?,
                end_occupancy_stripped = ?, end_position_stripped = ?,
                technique_steps = ?, main_ideas = ?, extract_json = ?, embedding = ?
            WHERE video_file = ? AND chapter_title = ? AND chapter_start = ?
              AND kind = ? AND array_index = ?
            """,
            (
                status,
                hops["named_move"],
                hops["ruleset"],
                hops["move_type"],
                hops["start_occupancy"],
                hops["start_position"],
                hops["end_occupancy"],
                hops["end_position"],
                stripped["named_move"],
                stripped["ruleset"],
                stripped["move_type"],
                stripped["start_occupancy"],
                stripped["start_position"],
                stripped["end_occupancy"],
                stripped["end_position"],
                steps,
                ideas,
                json.dumps(extract),
                embedding,
                current["video_file"],
                current["chapter_title"],
                current["chapter_start"],
                current["kind"],
                current["array_index"],
            ),
        )
        self._conn.commit()
        if write_back_corpus:
            self._write_back_technique(current, extract)

    def _load_sql(self, row) -> sqlite3.Row:
        found = self._conn.execute(
            """
            SELECT * FROM extract
            WHERE video_file = ? AND chapter_title = ? AND chapter_start = ?
              AND kind = ? AND array_index = ?
            """,
            (
                row.video_file,
                row.chapter_title,
                row.chapter_start,
                row.kind,
                row.array_index,
            ),
        ).fetchone()
        if found is None:
            raise ValueError("Row is not in the extracted index")
        return found

    def _write_back_technique(self, current: sqlite3.Row, extract: dict) -> None:
        path_value = current["corpus_json_path"]
        if not path_value:
            return
        path = Path(path_value)
        if not path.is_file():
            return
        payload = json.loads(path.read_text(encoding="utf-8"))
        chapters = payload.get("chapters")
        if not isinstance(chapters, list):
            return
        for chapter in chapters:
            if not isinstance(chapter, dict):
                continue
            title = chapter.get("title")
            if not isinstance(title, str):
                title = ""
            try:
                start = float(chapter.get("start"))
            except (TypeError, ValueError):
                start = 0.0
            if title != current["chapter_title"] or start != current["chapter_start"]:
                continue
            techniques = chapter.get("techniques")
            if not isinstance(techniques, list):
                return
            array_index = current["array_index"]
            if array_index < 0 or array_index >= len(techniques):
                return
            techniques[array_index] = extract
            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            return

    def _technique_embed_text(self, named_move: str, steps: str, ideas: str) -> str:
        return " ".join(part for part in (named_move, steps, ideas) if part)

    def _upsert(
        self,
        *,
        video_file: str,
        chapter_title: str,
        chapter_start: float,
        kind: str,
        array_index: int,
        status: str,
        hops: dict[str, str],
        technique_steps: str,
        main_ideas: str,
        concept: str,
        instructor: str,
        instructional: str,
        extract: dict,
        corpus_json_path: str,
        embedding: bytes | None,
    ) -> None:
        stripped = {field: hops[field].rstrip("*") for field in HOP_FIELDS}
        tags = extract.get("suggested_tags") if isinstance(extract, dict) else []
        ranges = extract.get("source_time_ranges") if isinstance(extract, dict) else []
        self._conn.execute(
            """
            INSERT OR REPLACE INTO extract (
                video_file, chapter_title, chapter_start, kind, array_index,
                status, named_move, ruleset, move_type, start_occupancy,
                start_position, end_occupancy, end_position,
                named_move_stripped, ruleset_stripped, move_type_stripped,
                start_occupancy_stripped, start_position_stripped,
                end_occupancy_stripped, end_position_stripped,
                technique_steps, main_ideas, suggested_tags, source_time_ranges,
                concept, instructor, instructional, corpus_json_path, extract_json,
                embedding
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?
            )
            """,
            (
                video_file,
                chapter_title,
                chapter_start,
                kind,
                array_index,
                status,
                hops["named_move"],
                hops["ruleset"],
                hops["move_type"],
                hops["start_occupancy"],
                hops["start_position"],
                hops["end_occupancy"],
                hops["end_position"],
                stripped["named_move"],
                stripped["ruleset"],
                stripped["move_type"],
                stripped["start_occupancy"],
                stripped["start_position"],
                stripped["end_occupancy"],
                stripped["end_position"],
                technique_steps,
                main_ideas,
                json.dumps(tags if isinstance(tags, list) else []),
                json.dumps(ranges if isinstance(ranges, list) else []),
                concept,
                instructor,
                instructional,
                corpus_json_path,
                json.dumps(extract),
                embedding,
            ),
        )
        self._conn.commit()

    def _embedding_blob(self, text: str) -> bytes | None:
        if self._embedder is None:
            return None
        vector = self._embedder(text)
        return array.array("f", vector).tobytes()

    def _row_from_sql(self, row: sqlite3.Row) -> ExtractedRow:
        extract = json.loads(row["extract_json"] or "{}")
        return ExtractedRow(
            video_file=row["video_file"],
            chapter_title=row["chapter_title"],
            chapter_start=row["chapter_start"],
            kind=row["kind"],
            array_index=row["array_index"],
            status=row["status"],
            named_move=row["named_move"],
            ruleset=row["ruleset"],
            move_type=row["move_type"],
            start_occupancy=row["start_occupancy"],
            start_position=row["start_position"],
            end_occupancy=row["end_occupancy"],
            end_position=row["end_position"],
            technique_steps=row["technique_steps"],
            main_ideas=row["main_ideas"],
            concept=row["concept"],
            instructor=row["instructor"],
            instructional=row["instructional"],
            extract=extract,
        )
