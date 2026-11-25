# Local storage engines for search, hierarchy, and LLM retrieval

Research for [Research: Local storage engines for search, hierarchy, and LLM retrieval](https://github.com/djsciman/video_transcriber_rag/issues/103). Re-performed 2026-11-25. Parent: [Extracted-technique data source for the curated store](https://github.com/djsciman/video_transcriber_rag/issues/101).

**Question:** which local-first storage engines can support full-text search, hierarchical or faceted browse on hop fields, and a path for LLM or embedding retrieval of extracted techniques on the coach's Windows machine?

This note compares candidates. It does **not** lock an engine. [Grilling: Lock storage engine, indexes, and playback keys](https://github.com/djsciman/video_transcriber_rag/issues/112) locks one after access methods and physical layout are decided.

Engine names belong in a later spec. Coach-facing screens keep glossary words.

## Constraints

- Coach's machine only. No cloud-hosted store.
- Windows, Python 3.12 (`py -3`), bind `127.0.0.1`.
- Hardware: Intel i9-9980HK, ~32 GB RAM, GTX 1650 4 GB. 4B local models are the on-box class.
- One findable row is one **extracted technique**.
- Evaluable for: keyword/FTS; filter or hierarchy on start/end occupancy and position, type of move, named move, instructor; video playback keys (volume file name + time range); optional embeddings or LLM extraction.
- OSI-licensed, with a recorded security process. Note daemon vs embedded library.

## Live row grain (from the 2026-11-25 corpus re-scan)

Sibling [Research: Prepared chapter JSON and extracted-technique fields](https://github.com/djsciman/video_transcriber_rag/issues/102) and [Task: Count extracted techniques in the prepared corpus](https://github.com/djsciman/video_transcriber_rag/issues/105) now have measured rows:

- **5378** extracted-technique objects across **450** volumes (558 JSON files, 86 instructionals).
- Hop strings on the technique object: `named_move`, `ruleset`, `move_type`, `start_occupancy`, `start_position`, `end_occupancy`, `end_position` (5259 starred values).
- FTS text: `technique_steps`, `main_ideas`, named-move text, chapter `transcript_cleaned`, chapter `concepts`.
- Keyword facets beyond hops: chapter and technique `suggested_tags` (string arrays, not hop objects).
- Playback columns: `video_file` basename, relative mirrored folder (JSON parent, including `Season 01`), `source_time_ranges` (almost always `[]` today).
- Instructor / instructional / chapter `title` / `start` / `end` for hierarchy and missing-file lookup.

Thousands of rows: ordinary `WHERE`/`GROUP BY` indexes and brute-force vectors are enough. ANN is optional.

## Candidate comparison

Legend: **embedded** = in-process library. **daemon** = separate process, bind loopback.

| Candidate | Shape | FTS / keyword | Hop filter / hierarchy | Playback keys | Embedding / LLM path | License | Security process | Windows + py-3 notes |
|---|---|---|---|---|---|---|---|---|
| SQLite FTS5 | Embedded | `MATCH`, `bm25()`, phrases, prefix, NEAR, column filters; `UNINDEXED` for stored-only columns | SQL `WHERE`/`GROUP BY`/`INDEX` on hop columns | Ordinary columns (`video_file`, folder, range strings) | Pair with sqlite-vec `vec0` | Public domain | [sqlite.org/security.html](https://www.sqlite.org/security.html) | Stdlib `sqlite3` **3.49.1** here; `ENABLE_FTS5`; `MATCH 'underhook'` returned the row; `enable_load_extension(True)` works |
| sqlite-vec | Embedded extension | None by itself | Metadata / partition columns on `vec0` | Store as metadata | `vec0` KNN | Apache-2.0 **or** MIT | `SECURITY.md` email alexsebastian.garcia@gmail.com | Stable PyPI **0.1.9** `win_amd64`; still **pre-v1**. Pre-release `0.1.10a4` (2026-05) has a reported Windows Smart App Control block of unsigned `vec0.dll` ([issue 368](https://github.com/asg017/sqlite-vec/issues/368), 2026-11-17). Prefer 0.1.9 until a signed wheel exists |
| DuckDB `fts` + `vss` | Embedded | `PRAGMA create_fts_index` + `match_bm25` | SQL `WHERE` on hop columns | Ordinary columns | Experimental HNSW `vss`; RAM-only unless experimental persistence flag | MIT | [Securing DuckDB](https://duckdb.org/docs/stable/operations_manual/securing_duckdb/overview.html) | `pip install duckdb`; Python 3.11+ |
| LanceDB Embedded | Embedded, local dir, no server | Native FTS, BM25, `query_type="fts"`; `where` pre/post filter | `where` on hop columns | Ordinary columns | Vector + hybrid (RRF default reranker) | Apache-2.0 | GitHub Security Advisories on `lancedb/lancedb` | `pip install lancedb`; default wheel is x86-64-haswell (AVX2); i9-9980HK is in range |
| PostgreSQL + pgvector | Daemon (`postgres`) | `tsvector` / `tsquery` | SQL indexes, btree, JSONB | Ordinary columns | pgvector ANN + hybrid with `tsvector` | PostgreSQL License (OSI) + pgvector PostgreSQL-style | PostgreSQL security team; CVE process | Windows installer; `listen_addresses` default `localhost` |
| Meilisearch CE | Daemon, default `:7700` | Typo-tolerant keyword search | `filterableAttributes`, facets, `facetDistribution` | Document fields | Vector store exists in product; CE vs EE split | CE MIT; EE BUSL (**not OSI**) | `SECURITY.md`: security@meilisearch.com; latest stable only; 72h | Official: Windows Server 2022+. Windows 10+ "may work". Docker is the documented Windows path |
| Typesense | Daemon, default `:8108` | Typo-tolerant search, faceting | Facets / filters | Document fields | Built-in embeddings / RAG features | GPL-3.0 (OSI) | `SECURITY.md`: security@typesense.org | **No native Windows binary**; WSL or Docker |
| Qdrant (Docker) | Daemon `:6333` REST / `:6334` gRPC | Sparse / full-text payload search in product | Payload filters + payload indexes; facet APIs | Payload fields | Native vector DB | Apache-2.0 | Default **no auth**; security docs; GitHub advisories | Docker; bind loopback |
| Qdrant client local mode | Embedded Python | Same API as server in local mode | Payload filters | Payload fields | Same API; optional FastEmbed on CPU | Apache-2.0 (client) | Same as Qdrant; local mode is development / prototyping | `QdrantClient(":memory:")` or `path="..."` |
| Qdrant Edge | Embedded library | Query API | `filter`, `facet()` | Payload | On-disk `EdgeShard` | Apache-2.0 | Product security docs | `qdrant-edge-py` |
| Chroma PersistentClient | Embedded (or optional Docker `:8000`) | Keyword / metadata where | Metadata filters | Metadata | Native embeddings collections | Apache-2.0 | **No `SECURITY.md` on `chroma-core/chroma` main** at prior research; not used as a lock candidate without a recorded channel | `PersistentClient(path=...)`; `CloudClient` is cloud-only and out |
| Tantivy | Library, not a store | Lucene-like BM25, facets, hierarchical facet fields | Hierarchical facets | Application-owned | Pair with a vector crate | MIT | `SECURITY.md` on `quickwit-oss/tantivy` | Python via `tantivy-py`; documents are immutable (delete + reindex to edit) |

Combinations that cover FTS **and** embeddings in one process: SQLite FTS5 + sqlite-vec; DuckDB `fts` + `vss`; Postgres FTS + pgvector; LanceDB hybrid. Search daemons cover FTS + facets with an extra process. Vector-first engines cover embeddings + payload filters; keyword FTS is secondary or paired.

## This machine (re-checked)

- CPU: Intel i9-9980HK (AVX2). LanceDB default Haswell wheel is in range.
- RAM: ~32 GB. 5378 rows plus 4B-class embeddings fit in RAM. DuckDB `vss` "must be able to fit into RAM" is satisfied at this scale.
- GPU: GTX 1650 4 GB. Local embeddings are CPU / small ONNX (FastEmbed class).
- Bind: any daemon on `127.0.0.1`. Qdrant Docker default has **no encryption or authentication**.
- Python: `py -3` is 3.12. This worktree: SQLite 3.49.1, `ENABLE_FTS5`, FTS `MATCH` succeeded, `enable_load_extension(True)` succeeded.

## Re-verification notes (vs 2026-11-19)

- **Scale is no longer hypothetical.** 5378 rows is the number a lock ticket should size against, not "eventually thousands."
- **Facets include keyword tags.** Chapter and technique `suggested_tags` are string arrays derived from `concepts` / `main_ideas`. Hop objects are no longer stored in `suggested_tags`.
- **Playback time ranges are sparse.** An engine must store `video_file` + relative folder even when `source_time_ranges` is `[]`. Filling starts is processing, not an engine requirement.
- **sqlite-vec** stable wheel remains 0.1.9 and pre-v1. Do not take `0.1.10a4` on this Windows laptop without a signed DLL; Smart App Control has blocked the unsigned `vec0.dll` ([asg017/sqlite-vec#368](https://github.com/asg017/sqlite-vec/issues/368)).
- **DuckDB `vss`** remains experimental. First-party docs (stable 1.4 / 2.0 FTS pages) still gate HNSW persistence behind `hnsw_enable_experimental_persistence` and warn about WAL recovery / crash corruption. FTS still defaults to `incremental = 0`.
- Cloud hosts, Meilisearch EE (BUSL), Elasticsearch SSPL, and Chroma `CloudClient` stay out.

## What still fits

Several local-first engines cover keyword/FTS, hop-field filter or facet browse, video playback columns, and an optional embedding path on this chassis. No engine is locked.

Embedded shortlist for a later lock: SQLite FTS5 (+ sqlite-vec 0.1.9 if vectors land), DuckDB `fts` (brute-force distance until `vss` persistence is non-experimental), LanceDB Embedded hybrid.

Daemon shortlist: Postgres+pgvector on localhost; Meilisearch CE on `:7700` (Docker on this laptop); Typesense GPL-3 via Docker/WSL; Qdrant Docker with loopback and auth enabled, or qdrant-client path mode for prototypes.

Operational burden (another daemon vs an embedded library) is a grilling input, not decided here.

## Out of scope

- Locking an engine.
- Implementing the store.
- Query-time embedding model choice (map fog).
- Cloud-hosted anything.

## Sources

- Live corpus walk 2026-11-25; sibling findings `prepared-chapter-json.md`, `corpus-extract-counts.md`
- SQLite FTS5: [sqlite.org/fts5.html](https://www.sqlite.org/fts5.html), [sqlite.org/security.html](https://www.sqlite.org/security.html); local `pragma compile_options` / `MATCH`
- sqlite-vec: [github.com/asg017/sqlite-vec](https://github.com/asg017/sqlite-vec) README (pre-v1), dual Apache-2.0/MIT, PyPI 0.1.9; [issue 368](https://github.com/asg017/sqlite-vec/issues/368)
- DuckDB FTS: [docs 2.0 FTS](https://duckdb.org/docs/2.0/core_extensions/full_text_search.html); VSS: [docs stable VSS](https://duckdb.org/docs/stable/core_extensions/vss) persistence warning
- LanceDB FTS / hybrid: [docs.lancedb.com/search/full-text-search](https://docs.lancedb.com/search/full-text-search)
- PostgreSQL FTS ch. 12; pgvector README; Meilisearch CE MIT vs EE BUSL; Typesense GPL-3 install guide (WSL/Docker); Qdrant quickstart / security (default no auth)
- Hardware class from map Notes
