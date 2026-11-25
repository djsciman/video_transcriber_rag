"""Extracted index of unreviewed techniques, approved techniques, and concepts."""

from __future__ import annotations

import array
import json
import math
import os
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from coach_app.citations import playback_handle, resolve_video_playback

_RANGE = re.compile(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)")

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

HOP_WALK_FILTERS = (
    "start_occupancy",
    "start_position",
    "move_type",
    "end_occupancy",
    "end_position",
    "named_move",
    "instructor",
)
SENTENCE_FIND_HOPS = HOP_FIELDS + ("instructor",)

_ROW_SELECT = """
            SELECT video_file, chapter_title, chapter_start, kind, array_index,
                   status, named_move, ruleset, move_type, start_occupancy,
                   start_position, end_occupancy, end_position, technique_steps,
                   main_ideas, concept, instructor, instructional,
                   transcript_folder, corpus_json_path, extract_json
            FROM extract
"""

_ROW_ORDER = "video_file, chapter_start, kind, array_index"

_FTS_COLUMNS = (
    "named_move",
    "instructor",
    "instructional",
    "chapter_title",
    "technique_steps",
    "main_ideas",
    "suggested_tags",
    "concept",
)

MINILM_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MINILM_PROVIDERS = ["CPUExecutionProvider"]

SENTENCE_FIND_VENDORS = (
    {
        "provider": "anthropic",
        "model": "claude-haiku-5-5",
        "key_env": "ANTHROPIC_API_KEY",
    },
    {
        "provider": "openai",
        "model": "gpt-5.4-mini",
        "key_env": "OPENAI_API_KEY",
    },
    {
        "provider": "xai",
        "model": "grok-4.3",
        "key_env": "XAI_API_KEY",
    },
)
SENTENCE_FIND_SPEC = (
    "Return a JSON object only. Fill hop fields when the sentence names them "
    "(named_move, ruleset, move_type, start_occupancy, start_position, "
    "end_occupancy, end_position, instructor). Leave unknown hops as empty "
    "strings. Put search keywords in a keywords array. Put one short English "
    "find-string in find_string for vector search. Do not write teaching "
    "advice. Do not explain how to perform a move."
)
SENTENCE_FIND_TIMEOUT = 30.0


def TextEmbedding(*args, **kwargs):
    """FastEmbed constructor seam. Lazy-imports so tests never load the model."""
    from fastembed import TextEmbedding as FastEmbedTextEmbedding

    return FastEmbedTextEmbedding(*args, **kwargs)


class MiniLMEmbedder:
    """CPU MiniLM-L6 via FastEmbed. Same model for ingest and query; no prefix."""

    def __init__(self, model=None) -> None:
        if model is None:
            model = TextEmbedding(
                model_name=MINILM_MODEL_ID,
                providers=MINILM_PROVIDERS,
            )
        self._model = model

    def __call__(self, text: str) -> list[float]:
        return self.embed_query(text)

    def embed_query(self, text: str) -> list[float]:
        vector = next(iter(self._model.embed([text])))
        if hasattr(vector, "tolist"):
            vector = vector.tolist()
        return [float(x) for x in vector]


@dataclass(frozen=True)
class Showing:
    start: float
    end: float
    playback_link: str | None = None


@dataclass(frozen=True)
class Playback:
    path: Path
    speech_start: float
    available: bool


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
    transcript_folder: str = ""
    corpus_json_path: str = ""
    showings: tuple[Showing, ...] = ()


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

    def ingest_chapter(
        self,
        volume,
        chapter,
        corpus_json_path=None,
        transcript_folder=None,
    ) -> None:
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
        json_path = _library_relative(corpus_json_path)
        folder = _transcript_folder(transcript_folder, json_path)
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
                    transcript_folder=folder,
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
                    transcript_folder=folder,
                    corpus_json_path=json_path,
                    embedding=embedding,
                )

    def embedding(self, row: ExtractedRow) -> tuple[float, ...] | None:
        cursor = self._conn.execute(
            """
            SELECT embedding FROM extract
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
        )
        sql_row = cursor.fetchone()
        if sql_row is None or sql_row["embedding"] is None:
            return None
        return tuple(array.array("f", sql_row["embedding"]))

    def embed_query(self, text: str) -> list[float]:
        embedder = self._resolve_embedder()
        if hasattr(embedder, "embed_query"):
            return list(embedder.embed_query(text))
        return list(embedder(text))

    def rows(self) -> tuple[ExtractedRow, ...]:
        return self._query_rows()

    def hop_walk(self, **filters) -> tuple[ExtractedRow, ...]:
        unknown = sorted(name for name in filters if name not in HOP_WALK_FILTERS)
        if unknown:
            raise TypeError(f"unsupported hop_walk filters: {', '.join(unknown)}")
        clauses = ["kind = 'technique'"]
        params: list[str] = []
        for field in HOP_WALK_FILTERS:
            values = _filter_values(filters.get(field))
            if not values:
                continue
            if field == "instructor":
                column = "instructor"
                chips = values
            else:
                column = f"{field}_stripped"
                chips = tuple(value.rstrip("*") for value in values)
            placeholders = ", ".join("?" for _ in chips)
            clauses.append(f"{column} IN ({placeholders})")
            params.extend(chips)
        return self._query_rows(" AND ".join(clauses), tuple(params))

    def siblings(
        self,
        row_or_instructional: ExtractedRow | str,
        video_file: str | None = None,
        chapter_title: str | None = None,
        chapter_start: float | None = None,
    ) -> tuple[ExtractedRow, ...]:
        exclude_kind = None
        exclude_index = None
        if isinstance(row_or_instructional, ExtractedRow):
            instructional = row_or_instructional.instructional
            video_file = row_or_instructional.video_file
            chapter_title = row_or_instructional.chapter_title
            chapter_start = row_or_instructional.chapter_start
            exclude_kind = row_or_instructional.kind
            exclude_index = row_or_instructional.array_index
        else:
            instructional = row_or_instructional
        clauses = [
            "instructional = ?",
            "video_file = ?",
            "chapter_title = ?",
            "chapter_start = ?",
        ]
        params: list[object] = [
            instructional,
            video_file,
            chapter_title,
            chapter_start,
        ]
        if exclude_kind is not None:
            clauses.append("NOT (kind = ? AND array_index = ?)")
            params.extend((exclude_kind, exclude_index))
        return self._query_rows(" AND ".join(clauses), tuple(params))

    def resolve_playback(self, row: ExtractedRow, showing: Showing, *, video_root) -> Playback:
        path, speech_start, available = resolve_video_playback(
            video_root=video_root,
            transcript_folder=row.transcript_folder,
            video_file=row.video_file,
            speech_start=showing.start,
        )
        return Playback(path=path, speech_start=speech_start, available=available)

    def cleaned_speech(self, row: ExtractedRow, corpus_root) -> str | None:
        if not row.corpus_json_path:
            return None
        path = Path(corpus_root) / row.corpus_json_path
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        chapters = payload.get("chapters") if isinstance(payload, dict) else None
        if not isinstance(chapters, list):
            return None
        for chapter in chapters:
            if not isinstance(chapter, dict):
                continue
            start = chapter.get("start")
            try:
                chapter_start = float(start)
            except (TypeError, ValueError):
                continue
            if chapter_start != row.chapter_start:
                continue
            cleaned = chapter.get("transcript_cleaned")
            return cleaned if isinstance(cleaned, str) else None
        return None

    def keyword_search(self, query, kind="both") -> tuple[ExtractedRow, ...]:
        text = query.strip() if isinstance(query, str) else ""
        if not text:
            return ()
        sql = f"""
            {_ROW_SELECT}
            WHERE rowid IN (
                SELECT rowid FROM extract_fts WHERE extract_fts MATCH ?
            )
        """
        params: list[str] = [text]
        if kind == "techniques":
            sql += " AND kind = ?"
            params.append("technique")
        elif kind == "concepts":
            sql += " AND kind = ?"
            params.append("concept")
        elif kind != "both":
            raise ValueError("kind must be 'techniques', 'concepts', or 'both'")
        sql += " ORDER BY video_file, chapter_start, kind, array_index"
        cursor = self._conn.execute(sql, params)
        return tuple(self._row_from_sql(row) for row in cursor)

    def sentence_find(self, sentence, kind="both") -> tuple[ExtractedRow, ...]:
        if kind == "techniques":
            kind_value = "technique"
        elif kind == "concepts":
            kind_value = "concept"
        elif kind == "both":
            kind_value = None
        else:
            raise ValueError("kind must be 'techniques', 'concepts', or 'both'")
        parsed = self._sentence_find_query(sentence)
        if parsed is None:
            return ()
        hops, keywords, find_string = parsed
        query = self.embed_query(find_string)
        walk_hops = {
            field: value
            for field, value in hops.items()
            if field in HOP_WALK_FILTERS
        }
        hop_ids = None
        if walk_hops:
            hop_ids = {_row_id(row) for row in self.hop_walk(**walk_hops)}
        ruleset = hops.get("ruleset")
        if isinstance(ruleset, str) and ruleset.strip():
            wanted = ruleset.strip().rstrip("*")
            matching = {
                _row_id(row)
                for row in self.rows()
                if row.kind == "technique" and row.ruleset.rstrip("*") == wanted
            }
            hop_ids = matching if hop_ids is None else hop_ids & matching
        keyword_ids = None
        if keywords:
            matched: set[tuple] | None = None
            for word in keywords:
                ids = {_row_id(row) for row in self.keyword_search(word, kind=kind)}
                matched = ids if matched is None else matched & ids
            keyword_ids = matched or set()
        scored: list[tuple[int, float, ExtractedRow]] = []
        for row in self.rows():
            if kind_value is not None and row.kind != kind_value:
                continue
            ident = _row_id(row)
            hop_ok = hop_ids is None or ident in hop_ids
            keyword_ok = keyword_ids is None or ident in keyword_ids
            full = row.kind == "technique" and hop_ok and keyword_ok
            similarity = _cosine(query, self.embedding(row))
            scored.append((0 if full else 1, -similarity, row))
        scored.sort(key=lambda item: (item[0], item[1]))
        return tuple(item[2] for item in scored)

    def save(self, row, fields, *, write_back_corpus=False, corpus_root=None) -> None:
        self._write_finder(
            row,
            fields,
            accept=False,
            write_back_corpus=write_back_corpus,
            corpus_root=corpus_root,
        )

    def save_and_accept(
        self, row, fields, *, write_back_corpus=False, corpus_root=None
    ) -> None:
        self._write_finder(
            row,
            fields,
            accept=True,
            write_back_corpus=write_back_corpus,
            corpus_root=corpus_root,
        )

    def accept(self, row, *, write_back_corpus=False, corpus_root=None) -> None:
        self._write_finder(
            row,
            {},
            accept=True,
            write_back_corpus=write_back_corpus,
            corpus_root=corpus_root,
        )

    def save_many(self, rows, fields, *, write_back_corpus=False, corpus_root=None) -> None:
        for item in rows:
            self.save(
                item,
                fields,
                write_back_corpus=write_back_corpus,
                corpus_root=corpus_root,
            )

    def save_and_accept_many(
        self, rows, fields, *, write_back_corpus=False, corpus_root=None
    ) -> None:
        for item in rows:
            self.save_and_accept(
                item,
                fields,
                write_back_corpus=write_back_corpus,
                corpus_root=corpus_root,
            )

    def close(self) -> None:
        self._conn.close()

    def _query_rows(
        self,
        where: str | None = None,
        params: tuple = (),
    ) -> tuple[ExtractedRow, ...]:
        sql = _ROW_SELECT
        if where:
            sql += f" WHERE {where}"
        sql += f" ORDER BY {_ROW_ORDER}"
        cursor = self._conn.execute(sql, params)
        return tuple(self._row_from_sql(row) for row in cursor)

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
        fts_cols = ", ".join(_FTS_COLUMNS)
        new_fts_vals = ", ".join(f"new.{col}" for col in _FTS_COLUMNS)
        old_fts_vals = ", ".join(f"old.{col}" for col in _FTS_COLUMNS)
        self._conn.execute(
            f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS extract_fts USING fts5(
                {fts_cols},
                content='extract',
                content_rowid='rowid'
            )
            """
        )
        self._conn.execute(
            f"""
            CREATE TRIGGER IF NOT EXISTS extract_fts_ai AFTER INSERT ON extract BEGIN
                INSERT INTO extract_fts(rowid, {fts_cols})
                VALUES (new.rowid, {new_fts_vals});
            END
            """
        )
        self._conn.execute(
            f"""
            CREATE TRIGGER IF NOT EXISTS extract_fts_ad AFTER DELETE ON extract BEGIN
                INSERT INTO extract_fts(extract_fts, rowid, {fts_cols})
                VALUES ('delete', old.rowid, {old_fts_vals});
            END
            """
        )
        self._conn.execute(
            f"""
            CREATE TRIGGER IF NOT EXISTS extract_fts_au AFTER UPDATE ON extract BEGIN
                INSERT INTO extract_fts(extract_fts, rowid, {fts_cols})
                VALUES ('delete', old.rowid, {old_fts_vals});
                INSERT INTO extract_fts(rowid, {fts_cols})
                VALUES (new.rowid, {new_fts_vals});
            END
            """
        )
        self._conn.execute("INSERT INTO extract_fts(extract_fts) VALUES ('rebuild')")
        for column in (
            "named_move_stripped",
            "ruleset_stripped",
            "move_type_stripped",
            "start_occupancy_stripped",
            "start_position_stripped",
            "end_occupancy_stripped",
            "end_position_stripped",
            "instructor",
            "status",
        ):
            self._conn.execute(
                f"CREATE INDEX IF NOT EXISTS extract_{column} ON extract({column})"
            )
        self._conn.execute(
            """
            CREATE INDEX IF NOT EXISTS extract_siblings
            ON extract(instructional, video_file, chapter_title, chapter_start)
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

    def _write_finder(
        self,
        row,
        fields,
        *,
        accept: bool,
        write_back_corpus: bool,
        corpus_root=None,
    ) -> None:
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
            self._write_back_technique(current, extract, corpus_root=corpus_root)

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

    def _write_back_technique(
        self, current: sqlite3.Row, extract: dict, corpus_root=None
    ) -> None:
        path_value = current["corpus_json_path"]
        if not path_value:
            return
        path = Path(path_value)
        if corpus_root is not None:
            path = Path(corpus_root) / path_value
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
        transcript_folder: str,
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
                concept, instructor, instructional, transcript_folder,
                corpus_json_path, extract_json, embedding
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?,
                ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?
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
                transcript_folder,
                corpus_json_path,
                json.dumps(extract),
                embedding,
            ),
        )
        self._conn.commit()

    def _sentence_find_query(self, sentence):
        try:
            chat = self._chat
            if chat is None:
                chat = production_sentence_find_chat
            raw = chat(sentence)
        except Exception:
            return None
        payload = _parse_json_object(raw)
        if payload is None:
            return None
        find_string = payload.get("find_string")
        if not isinstance(find_string, str):
            find_string = ""
        return _filled_hops(payload), _filled_keywords(payload), find_string.strip()

    def _resolve_embedder(self):
        if self._embedder is None:
            self._embedder = MiniLMEmbedder()
        return self._embedder

    def _embedding_blob(self, text: str) -> bytes | None:
        vector = self._resolve_embedder()(text)
        return array.array("f", vector).tobytes()

    def _row_from_sql(self, row: sqlite3.Row) -> ExtractedRow:
        extract = json.loads(row["extract_json"] or "{}")
        ranges = extract.get("source_time_ranges") if isinstance(extract, dict) else []
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
            transcript_folder=row["transcript_folder"],
            corpus_json_path=row["corpus_json_path"],
            showings=_parse_showings(ranges, row["video_file"]),
        )


def complete_sentence_find_vendor(
    prompt,
    *,
    provider,
    model,
    urlopen=None,
    timeout=SENTENCE_FIND_TIMEOUT,
):
    from bjj_pipeline.prepare import complete_chat

    return complete_chat(
        prompt,
        provider=provider,
        model=model,
        spec=SENTENCE_FIND_SPEC,
        urlopen=urlopen,
        timeout=timeout,
    )


def production_sentence_find_chat(sentence: str) -> dict:
    for vendor in SENTENCE_FIND_VENDORS:
        key = os.environ.get(vendor["key_env"], "")
        if not isinstance(key, str) or not key.strip():
            continue
        try:
            text = complete_sentence_find_vendor(
                sentence,
                provider=vendor["provider"],
                model=vendor["model"],
            )
        except Exception:
            continue
        payload = _parse_json_object(text)
        if payload is None:
            continue
        return payload
    raise RuntimeError("sentence find chat failed")


def _row_id(row) -> tuple:
    return (
        row.video_file,
        row.chapter_title,
        row.chapter_start,
        row.kind,
        row.array_index,
    )


def _cosine(left, right) -> float:
    if left is None or right is None:
        return 0.0
    if len(left) != len(right) or not left:
        return 0.0
    dot = 0.0
    left_norm = 0.0
    right_norm = 0.0
    for x, y in zip(left, right):
        fx = float(x)
        fy = float(y)
        dot += fx * fy
        left_norm += fx * fx
        right_norm += fy * fy
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (math.sqrt(left_norm) * math.sqrt(right_norm))


def _parse_json_object(raw):
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _filled_hops(payload: dict) -> dict[str, str]:
    source = payload
    nested = payload.get("hops")
    if isinstance(nested, dict):
        source = {**nested, **payload}
    hops: dict[str, str] = {}
    for field in SENTENCE_FIND_HOPS:
        value = source.get(field)
        if isinstance(value, str) and value.strip():
            hops[field] = value.strip()
    return hops


def _filled_keywords(payload: dict) -> tuple[str, ...]:
    value = payload.get("keywords", payload.get("keyword"))
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if not isinstance(value, list):
        return ()
    return tuple(
        item.strip() for item in value if isinstance(item, str) and item.strip()
    )


def _filter_values(value) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,) if value else ()
    return tuple(item for item in value if isinstance(item, str) and item)


def _library_relative(corpus_json_path) -> str:
    if corpus_json_path is None:
        return ""
    path = Path(corpus_json_path)
    if path.is_absolute():
        return path.name
    return path.as_posix()


def _transcript_folder(transcript_folder, json_path: str) -> str:
    if transcript_folder is not None:
        folder = Path(transcript_folder)
        if folder.is_absolute():
            return folder.name
        return folder.as_posix()
    if not json_path:
        return ""
    parent = Path(json_path).parent
    if parent.as_posix() in (".", ""):
        return ""
    return parent.as_posix()


def _parse_showings(ranges, video_file: str) -> tuple[Showing, ...]:
    values = ranges if isinstance(ranges, list) else []
    found: list[Showing] = []
    for item in values:
        if not isinstance(item, str):
            continue
        match = _RANGE.fullmatch(item.strip())
        if not match:
            continue
        start = float(match.group(1))
        end = float(match.group(2))
        found.append(
            Showing(
                start=start,
                end=end,
                playback_link=playback_handle(video_file, start),
            )
        )
    return tuple(found)
