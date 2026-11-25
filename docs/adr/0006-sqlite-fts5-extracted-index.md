---
status: accepted
---

# SQLite FTS5 extracted index with MiniLM-L6 blobs

The extracted index is a local store of a few thousand technique and concept rows that must support hop filters, keyword search, and local CPU vectors, with no cloud-hosted store and no extra daemon.

The spec names **SQLite with FTS5** as the engine, in its own file, separate from the curated store. Each row stores a 384-d float32 blob from FastEmbed `sentence-transformers/all-MiniLM-L6-v2` on CPU onnxruntime. Sentence find orders a band with cosine in process. sqlite-vec, DuckDB, LanceDB, and loopback search daemons are out.

One extract table holds both kinds. The primary key is `video_file` + chapter title + chapter start + kind + array index. The copied extract is JSON on the row; hops, status, instructor, instructional, playback keys, and the vector are first-class columns. FTS5 covers named move, instructor, instructional, chapter title, steps, main ideas, keyword tags, and the concept string. Hops persist as written; filters and facet chips use a stripped copy with the trailing `*` removed. Playback joins `video_root / transcript_folder / video_file` at open time.

## Considered options

- DuckDB `fts` + `vss`, LanceDB Embedded, Postgres+pgvector, Meilisearch CE, Typesense, Qdrant. Rejected: this machine already has SQLite 3.49.1 with FTS5; 5378 rows are ordinary SQL; a daemon is another process; DuckDB vector persistence is still experimental.
- sqlite-vec 0.1.9 (or 0.1.10a4). Rejected: pre-v1; the later unsigned Windows DLL is blocked on this laptop; 8.3 MB of 384-d vectors fit brute-force cosine.
- Arctic-xs, BGE-small, or BGE-base as the shared CPU model. Rejected: MiniLM-L6 ingest was 160 s here with no query prefix; hop and keyword bands already rank, so the vector only orders inside a band.
- One SQLite file shared with the curated store. Rejected: this map may name an engine for the extracted index; the curated store stays on its own seam.
- Two tables, one per kind. Rejected: keyword search already hits both kinds; hop columns stay empty on concept rows.

## Consequences

Prepare, Accept, and finder writes go to this SQLite file. The curated store does not gain a named engine here. A later scale jump large enough to need ANN can add sqlite-vec without changing hop columns or FTS5. Changing the embedding model re-embeds every row.
