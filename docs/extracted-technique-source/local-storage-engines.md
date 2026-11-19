# Local storage engines for search, hierarchy, and LLM retrieval

Research for [Research: Local storage engines for search, hierarchy, and LLM retrieval](https://github.com/djsciman/video_transcriber_rag/issues/103). Parent map: [Extracted-technique data source for the curated store](https://github.com/djsciman/video_transcriber_rag/issues/101).

**Question:** which local-first storage engines can support full-text search, hierarchical or faceted browse on hop fields, and a path for LLM or embedding retrieval of extracted techniques on the coach's Windows machine?

This note compares candidates. It does **not** lock an engine. [Grilling: Lock storage engine, indexes, and playback keys](https://github.com/djsciman/video_transcriber_rag/issues/112) locks one after access methods and physical layout are decided.

Engine names belong in a later spec. Coach-facing screens keep glossary words ([GLOSSARY.md](../../GLOSSARY.md): **extracted technique**, hop fields, instructor, volume). Production `coach_app/` is unchanged by this ticket.

## Constraints (from the ticket)

- Coach's machine only. No cloud-hosted store.
- Windows, Python 3.12 (`py -3`), bind `127.0.0.1`.
- Hardware class: Intel i9-9980HK, ~32 GB RAM, GTX 1650 4 GB. Treat 4B local models as the on-box class.
- One findable row is one **extracted technique**. Expected scale is hundreds of volumes and thousands of rows.
- Evaluable for: keyword/FTS; filter or hierarchy on start/end occupancy and position, type of move, named move, instructor; video playback keys (volume file name + time range); optional embeddings or LLM extraction if a later ticket requires them.
- OSI-licensed, with a recorded security process. Note daemon vs embedded library.

## Method

First-party docs, licenses, and security policies for each candidate. This worktree also ran a local SQLite FTS5 smoke check (`py -3`, SQLite 3.49.1, `ENABLE_FTS5`, `MATCH` on `butterfly sweep underhook`, `enable_load_extension` true). Scale claims stay at thousands of rows: ordinary `WHERE`/`GROUP BY` indexes and brute-force vectors are enough at that size; ANN indexes are optional later.

Row grain used for evaluation comes from the sibling research [Prepared chapter JSON for extracted techniques](https://github.com/djsciman/video_transcriber_rag/issues/102) (prompt + Marcelo sample shape): one object in a chapter `techniques` array, hop strings (`named_move`, `ruleset`, `move_type`, `start_occupancy`, `start_position`, `end_occupancy`, `end_position`), `technique_steps`, `main_ideas`, `source_time_ranges`, keyword `suggested_tags`, plus volume/chapter credits (`instructor`, instructional, `video_file` basename, chapter title/`start`/`end`). Facets of interest are those hop strings plus instructor. FTS text is `technique_steps`, `main_ideas`, named-move text, and cleaned chapter speech if ingest keeps it. Playback keys are volume file name plus time range (sibling playback research; this ticket only needs the engine to store those columns).

## Candidate comparison

Legend: **embedded** = in-process library in the Python app. **daemon** = separate process, bind loopback.

| Candidate | Shape | FTS / keyword | Hop filter / hierarchy | Playback keys | Embedding / LLM path | License | Security process | Windows + py-3 notes |
|---|---|---|---|---|---|---|---|---|
| SQLite FTS5 | Embedded | `MATCH`, `bm25()`, phrases, prefix, NEAR, column filters; `UNINDEXED` for stored-only columns | Ordinary SQL `WHERE`/`GROUP BY`/`INDEX` on hop columns | Ordinary columns (`video_file`, range strings) | Pair with sqlite-vec `vec0` | Public domain (Hwaci copyright page) | [sqlite.org/security.html](https://www.sqlite.org/security.html) | Stdlib `sqlite3` 3.49.1 here; FTS5 compiled in |
| sqlite-vec | Embedded extension | None by itself | Metadata / partition columns on `vec0` | Store as metadata | `vec0` KNN on float/int8/binary | Apache-2.0 **or** MIT | `SECURITY.md` email alexsebastian.garcia@gmail.com | PyPI 0.1.9 `win_amd64` wheel; **pre-v1** |
| DuckDB `fts` + `vss` | Embedded | `PRAGMA create_fts_index` + `match_bm25` | SQL `WHERE` on hop columns (example already mixes `score` with `doc_version > 2`) | Ordinary columns | Experimental HNSW `vss`; RAM-only unless experimental persistence flag | MIT | [Securing DuckDB](https://duckdb.org/docs/2.0/operations_manual/securing_duckdb/overview.html) | `pip install duckdb` 2.0.0; Python 3.11+ |
| LanceDB Embedded | Embedded, local dir, no server | Native FTS, BM25, `query_type="fts"`; `where` pre/post filter | `where` on hop columns | Ordinary columns | Vector + hybrid (RRF default reranker) | Apache-2.0 | GitHub Security Advisories on `lancedb/lancedb` | `pip install lancedb`; default wheel targets x86-64-haswell (AVX2); i9-9980HK is Haswell+ |
| PostgreSQL + pgvector | Daemon (`postgres`) | `tsvector` / `tsquery` (ch. 12) | SQL indexes, btree, JSONB | Ordinary columns | pgvector ANN + hybrid with `tsvector` | PostgreSQL License (OSI) + pgvector PostgreSQL-style | PostgreSQL security team; CVE process | Windows installer; `listen_addresses` default `localhost`; no Unix socket by default |
| Meilisearch CE | Daemon, default `:7700` | Typo-tolerant keyword search | `filterableAttributes`, facets, `facetDistribution` | Document fields | Vector store exists in product; CE vs EE split | CE MIT; EE BUSL (source-available, not OSI) | `SECURITY.md`: security@meilisearch.com; latest stable only; 72h | Official: Windows Server 2022+. Windows 10+ "may work". Docker is the documented Windows path |
| Typesense | Daemon, default `:8108` | Typo-tolerant search, faceting | Facets / filters | Document fields | Built-in embeddings / RAG features | GPL-3.0 (OSI) | `SECURITY.md`: security@typesense.org | **No native Windows binary**; WSL or Docker |
| Qdrant (Docker) | Daemon `:6333` REST / `:6334` gRPC | Sparse / full-text payload search in product | Payload filters + payload indexes; facet APIs | Payload fields | Native vector DB | Apache-2.0 | Default **no auth**; security docs; GitHub advisories | Docker; Windows named volume note |
| Qdrant client local mode | Embedded Python | Same API as server in local mode | Payload filters | Payload fields | Same API; optional FastEmbed on CPU | Apache-2.0 (client) | Same as Qdrant; local mode is "development, prototyping and testing" | `QdrantClient(":memory:")` or `path="..."` |
| Qdrant Edge | Embedded library | Query API | `filter`, `facet()` | Payload | On-disk `EdgeShard` | Apache-2.0 | Product security docs | `qdrant-edge-py`; separate from qdrant-client local mode |
| Chroma PersistentClient | Embedded (or optional Docker `:8000`) | Keyword / metadata where | Metadata filters | Metadata | Native embeddings collections | Apache-2.0 | **No `SECURITY.md` on `chroma-core/chroma` main** at research time (404) | `PersistentClient(path=...)`; `CloudClient` is cloud-only |
| Tantivy | Library, not a store | Lucene-like BM25, facets, hierarchical facet fields | Hierarchical facets | Application-owned | Pair with a vector crate | MIT | `SECURITY.md` on `quickwit-oss/tantivy` | Windows + Linux + macOS; Python via `tantivy-py`; documents are immutable (delete + reindex to edit) |
| USearch | Library, not a store | None | None | None | Dense/sparse ANN | Apache-2.0 | GitHub advisories | Python bindings; DuckDB `vss` uses usearch internally |

Combinations that cover FTS **and** embeddings in one process: SQLite FTS5 + sqlite-vec; DuckDB `fts` + `vss`; Postgres FTS + pgvector; LanceDB hybrid. Search daemons (Meilisearch, Typesense) cover FTS + facets with an extra process; pair with a vector library if embeddings land later. Vector-first engines (Qdrant, Chroma) cover embeddings + payload filters; keyword FTS is secondary or paired.

## This machine

- CPU: Intel i9-9980HK (Coffee Lake-H, AVX2). LanceDB's default Haswell (`x86-64-haswell`) wheel is in range; `lancedb-compat` is for older CPUs.
- RAM: ~32 GB. Thousands of rows plus 4B-class embeddings fit in RAM; DuckDB `vss` "must be able to fit into RAM" is satisfied at this scale.
- GPU: GTX 1650 4 GB. Local embeddings for this chassis are CPU / small ONNX (FastEmbed class). 4B generative models are the on-box class; 8B+ needs CPU offload.
- Bind: keep any daemon on `127.0.0.1`. Qdrant's documented Docker ports advertise `localhost`; default config has **no encryption or authentication**.
- Python: `py -3` is 3.12. DuckDB Python requires 3.11+. Meilisearch Python SDK documents >=3.10.

## Per-engine notes

### SQLite FTS5 (embedded)

Owner: [sqlite.org/fts5.html](https://sqlite.org/fts5.html).

FTS5 is a virtual table module. Create with `CREATE VIRTUAL TABLE ... USING fts5(col, ...)`. Query with `MATCH`, `=`, or table-valued function syntax. `ORDER BY rank` plus `bm25()` for relevance. Phrase, prefix (`*`), `NEAR`, boolean `AND`/`OR`/`NOT`, and per-column filters (`col : term` or `{col1 col2} : term`) are first-party. `UNINDEXED` stores a column without putting it in the FTS index (uuid example on the FTS5 page): hop IDs, instructor, `video_file`, and time-range strings can live as ordinary indexed SQL columns, with `technique_steps` / `main_ideas` in FTS.

Hierarchy at thousands of rows is SQL: `WHERE start_occupancy = 'bottom' AND move_type = 'sweep' GROUP BY start_position`. FTS5 is the keyword engine; btree indexes are the facet engine.

License: [sqlite.org/copyright.html](https://sqlite.org/copyright.html) — deliverable code dedicated to the public domain. OSI treats public-domain dedications as GPL-compatible; Hwaci also sells a Warranty of Title for jurisdictions that want a paper license.

Security: [sqlite.org/security.html](https://www.sqlite.org/security.html) — "Defense Against The Dark Arts": validate inputs, `SQLITE_DBCONFIG_DEFENSIVE`, authorizer, progress handler, heap limits, `trusted_schema=OFF` for untrusted files. Fuzz-tested. Bugs in SQL input or database files are treated as serious.

This worktree: CPython `sqlite3` 3.49.1, compile options include `ENABLE_FTS5`, in-memory `MATCH 'underhook'` returned the butterfly-sweep row, `enable_load_extension(True)` succeeded (needed if sqlite-vec is loaded as an extension).

Operational burden: none beyond the process already running `py -3 -m coach_app`. File on disk next to the app.

### sqlite-vec (embedded extension)

Owner: [github.com/asg017/sqlite-vec](https://github.com/asg017/sqlite-vec).

`CREATE VIRTUAL TABLE ... USING vec0(sample_embedding float[8])`. KNN via `WHERE sample_embedding MATCH '[...]' ORDER BY distance LIMIT k`. Float, int8, and binary vectors. Non-vector data in metadata, auxiliary, or partition key columns. Pure C, no deps, "runs anywhere SQLite runs" including Windows.

Python: `pip install sqlite-vec` ([alexgarcia.xyz/sqlite-vec/python.html](https://alexgarcia.xyz/sqlite-vec/python.html)). PyPI **0.1.9** ships `sqlite_vec-0.1.9-py3-none-win_amd64.whl`. README banner: *"sqlite-vec is a pre-v1, so expect breaking changes."* Dual [LICENSE-APACHE](https://github.com/asg017/sqlite-vec/blob/main/LICENSE-APACHE) + [LICENSE-MIT](https://github.com/asg017/sqlite-vec/blob/main/LICENSE-MIT).

Security: [SECURITY.md](https://github.com/asg017/sqlite-vec/blob/main/SECURITY.md) — report to alexsebastian.garcia@gmail.com; avoid public GitHub issues. One-line policy; recorded channel exists. PyPI 0.1.9 has no provenance attestations.

Pairing: FTS5 for keyword, `vec0` for optional embeddings, one `.db` file. Load via `enable_load_extension`. Sibling projects `sqlite-lembed` (local GGUF) and `sqlite-rembed` (remote APIs) are optional later; rembed talks to remote APIs and sits outside the local-first constraint if used for production embeddings.

### DuckDB `fts` + `vss` (embedded)

Owners: [Full-Text Search Extension](https://duckdb.org/docs/2.0/core_extensions/full_text_search.html), [Vector Similarity Search Extension](https://duckdb.org/docs/2.0/core_extensions/vss.html), [Python API](https://duckdb.org/docs/2.0/clients/python/overview.html). License: MIT ([github.com/duckdb/duckdb](https://github.com/duckdb/duckdb/blob/main/LICENSE)).

Python: `pip install duckdb`, stable client **2.0.0**, **Python 3.11 or newer**. Persistent file: `duckdb.connect("file.db")`. In-memory: `duckdb.connect()` or `duckdb.sql()`.

FTS: autoloaded `fts` extension, described as similar to SQLite FTS5. `PRAGMA create_fts_index(input_table, input_id, *input_values, ..., incremental = 0)`. Retrieval via `match_bm25(id, query, fields := ..., k, b, conjunctive)`. First-party example filters `doc_version > 2` **and** requires a BM25 score — hop `WHERE` clauses sit beside FTS in ordinary SQL. Default `incremental = 0`: index does not update on table changes unless `incremental = 1` (document id `NOT NULL` or `PRIMARY KEY`) or the index is rebuilt.

VSS: **experimental**. `CREATE INDEX ... USING HNSW (vec)` on `FLOAT` arrays only. Index lives in RAM ("must be able to fit into RAM"; size does not count toward `memory_limit`). Persistence of HNSW is off unless `SET hnsw_enable_experimental_persistence = true`; WAL recovery for custom indexes is incomplete, with a documented risk of data loss or corruption after a crash. At thousands of rows a brute-force `ORDER BY array_distance(...) LIMIT k` already works; HNSW is optional acceleration.

Security: [Securing DuckDB](https://duckdb.org/docs/2.0/operations_manual/securing_duckdb/overview.html) and [securing extensions](https://duckdb.org/docs/2.0/operations_manual/securing_duckdb/securing_extensions.html). Unsigned extensions require `allow_unsigned_extensions`. Community extensions are a separate repository.

Operational burden: embedded. Worker threads plus a default async I/O pool (4× cores, cap 256); configurable.

### LanceDB Embedded (embedded)

Owners: [Full-Text Search](https://docs.lancedb.com/search/full-text-search), GitHub [lancedb/lancedb](https://github.com/lancedb/lancedb) (Apache-2.0).

Embedded OSS is in-process. `lancedb.connect(uri)` opens a local directory. **No server** for Embedded. Python: `pip install lancedb`. Default wheel targets **x86-64-haswell** (AVX2+FMA+F16C). The i9-9980HK has AVX2; the default wheel is the one to use. `lancedb-compat` is for older CPUs.

FTS: `table.create_index("text", config=FTS())` then `table.search("puppy", query_type="fts", fts_columns="text")`. BM25; `_score` is relative relevance. `where(...)` with `prefilter=True`/`False` for hop predicates. New rows can sit outside the FTS index until `table.optimize()`; search still scans them. Native FTS does not take legacy Tantivy-only index parameters (Tantivy was an earlier FTS backend).

Hybrid: vector + FTS with RRF as the default reranker ([hybrid search](https://docs.lancedb.com/enterprise/v1-12-0/search/hybrid-search.md)). One table can hold hop columns, `video_file`, time ranges, a text column, and a vector column.

SQL query language is **Enterprise-only**. Embedded uses the Python/TS/Rust query API. That is enough for thousands of rows.

Phrase queries need `with_position=True`. Lance-based FTS documents that boolean `OR`/`AND` in the search **string** are unsupported; structured `MatchQuery` / `BooleanQuery` objects cover required/optional/excluded terms.

Operational burden: embedded. Index maintenance (`optimize`) is application-owned.

### PostgreSQL + pgvector (daemon)

Owners: [PostgreSQL FTS, chapter 12](https://www.postgresql.org/docs/current/textsearch.html); [listen_addresses](https://www.postgresql.org/docs/current/runtime-config-connection.html) default `localhost`; Windows: `unix_socket_directories` empty, so TCP loopback. License: [PostgreSQL License](https://www.postgresql.org/about/licence/) (OSI, BSD/MIT-like). pgvector: [github.com/pgvector/pgvector](https://github.com/pgvector/pgvector) v0.8.7, Windows build via `nmake` / `PGROOT`, LICENSE PostgreSQL-style. Hybrid retrieval with `tsvector` is documented in pgvector README.

FTS: `tsvector` / `tsquery`, ranking, dictionaries, GIN indexes. Hop filters: btree / GIN on columns or JSONB. Playback keys: ordinary columns. Embeddings: `vector` type, IVFFlat / HNSW indexes.

Operational burden: **a postgres service** on the coach laptop. Highest ops cost of the SQL candidates. Bind `listen_addresses = 'localhost'`. Auth is the usual `pg_hba.conf` local trust/scram. Security process is the PostgreSQL project's CVE / security-team channel.

Fits the constraints. The cost is installing and keeping a database server next to stdlib `http.server`.

### Meilisearch Community Edition (daemon)

Owner: [Install Meilisearch locally](https://www.meilisearch.com/docs/learn/getting_started/installation). Facets: [faceted search](https://www.meilisearch.com/docs/learn/fine_tuning_results/faceted_search) (`filterableAttributes`, `facetDistribution`).

CE is MIT. Enterprise is BUSL (source-available; **out of OSI** for this ticket — stay on CE). Default listen **7700**. Docker: `getmeili/meilisearch`, `-p 7700:7700`, PowerShell volume `${pwd}`.

Windows: **officially supported on Windows Server 2022 or later**. "Windows OS 10+ may work but is not officially supported." Documented Windows install paths: Docker, GitHub binary, Cygwin/WSL, or compile from source.

Python SDK is a separate MIT package (documents Python >=3.10).

Security: [SECURITY.md](https://github.com/meilisearch/meilisearch/blob/main/SECURITY.md) — security@meilisearch.com; GitHub issues are not the channel; latest stable only; 72-hour acknowledgement. Meilisearch Cloud is out of scope.

Hop browse: declare hop fields filterable/faceted. FTS is the product. Embeddings exist in the broader product; confirm CE vs EE before counting on vectors.

Operational burden: another daemon beside coach_app. Bind `127.0.0.1:7700`.

### Typesense (daemon)

Owner: [Install Typesense](https://typesense.org/docs/guide/install-typesense.html). License: [GPL-3.0](https://github.com/typesense/typesense/blob/master/LICENSE.txt) (OSI). Default port **8108**.

Windows: **WSL or Docker**. There is no first-party native Windows binary in the install guide.

Security: [SECURITY.md](https://github.com/typesense/typesense/blob/master/SECURITY.md) — security@typesense.org.

Facets and typo-tolerant search are core. Docker on loopback is the Windows path that stays local. Cloud Typesense is out of scope.

GPL-3 on a daemon the app talks to over HTTP is a license the later lock ticket can accept; it is a different shape than embedding MIT/Apache into the Python process.

### Qdrant: three local shapes

**Docker daemon** — [Local Quickstart](https://qdrant.tech/documentation/quickstart/). `docker run -p 6333:6333 -p 6334:6334 -v ... qdrant/qdrant`. REST `localhost:6333`, gRPC `6334`. Windows: named Docker volume instead of a bind mount may be required. **Default: no encryption or authentication.** "Anyone with network access to your machine can access your Qdrant container instance." Bind loopback and read [Security](https://qdrant.tech/documentation/security/). Payload filters on hop fields; payload indexes recommended for filtered search; vectors are native. Apache-2.0. Qdrant Cloud is out of scope.

**qdrant-client local mode** — [qdrant-client README](https://github.com/qdrant/qdrant-client): `QdrantClient(":memory:")` or `QdrantClient(path="path/to/db")`. "Local mode is useful for development, prototyping and testing." Same API, no server. Optional FastEmbed (`qdrant-client[fastembed]`) runs embeddings on CPU (ONNX); GPU extra is `fastembed-gpu`. FastEmbed on CPU matches this chassis better than the 4 GB GTX 1650. Cloud inference (`cloud_inference=True`) is out of scope.

**Qdrant Edge** — [Edge quickstart](https://qdrant.tech/documentation/edge/edge-quickstart/). Separate package `qdrant-edge-py`. `EdgeShard` on disk: query, filter, `facet()`, optimize, close. Documented as embedded, no separate server. Distinct from qdrant-client local mode.

Keyword FTS is not the primary story; payload + vectors + facet() cover hop browse and LLM retrieval. Pair with SQLite/DuckDB/Lance FTS if keyword search is first-class.

### Chroma (embedded PersistentClient)

Owner: [Getting started](https://docs.trychroma.com/docs/overview/getting-started), [Clients](https://docs.trychroma.com/docs/overview/chroma-clients). License: Apache-2.0.

- `CloudClient`: **cloud-only. Out of scope.**
- `Client()`: in-memory, **ephemeral**. Data gone when the process exits.
- `PersistentClient(path=...)`: on-disk, default directory `.chroma`. This is the local-first shape.
- Docker `chromadb/chroma` on `:8000` for TypeScript/Rust clients that need a server.

Metadata filters cover hop fields. Collections are embedding-native. Keyword search exists in current product APIs; confirm the local persistent client’s keyword path at lock time.

Security: **`https://github.com/chroma-core/chroma/blob/main/SECURITY.md` returned 404** at research time. Apache-2.0 is recorded; a first-party security-process file on main was not. That is a gap against the ticket’s “recorded security process” bar.

### Tantivy (library)

Owner: [quickwit-oss/tantivy](https://github.com/quickwit-oss/tantivy). MIT. Lucene-inspired Rust search library: BM25, facets, **hierarchical facet fields**. Windows + Linux + macOS. Python: `tantivy-py`. Documents are **immutable**; an edit is delete + reindex. `SECURITY.md` present.

Tantivy is an indexer, not a database. A later spec could use it behind a custom store. LanceDB’s current native FTS no longer takes Tantivy-only parameters.

### USearch (library)

Owner: [unum-cloud/usearch](https://github.com/unum-cloud/usearch). Apache-2.0. Header-only C++ proximity graph; Python bindings; Windows. Dense and sparse search. **No FTS.** DuckDB `vss` is usearch-based. Useful as a vector backend next to an FTS engine; not a store of extracted techniques by itself.

## Combinations (still candidates)

These pairings each cover keyword, hop filters, playback columns, and an embedding slot without leaving the laptop:

1. **SQLite FTS5 + sqlite-vec** — one file, stdlib already in coach_app’s process family, extension load for vectors. sqlite-vec is pre-v1.
2. **DuckDB `fts` + SQL hops** — BM25 + `WHERE` hops in one SQL engine. Add `vss` later; treat HNSW persistence as experimental.
3. **LanceDB Embedded hybrid** — FTS + vector + `where` in one local directory. AVX2 wheel matches this CPU. SQL language is Enterprise-only.
4. **Postgres FTS + pgvector** — mature FTS + ANN. Cost is a local postgres daemon.
5. **Meilisearch CE (or Typesense in Docker) for FTS/facets**, SQLite or files for playback keys, optional later vector lib — extra daemon, strong faceted UX APIs.
6. **Qdrant local path / Edge + a keyword engine** — vector-first if LLM retrieval leads; keyword still needs a partner for FTS5-class phrases.

## Considered and dropped (or scoped out)

| Name | Why it leaves this comparison |
|---|---|
| Meilisearch Cloud, Typesense Cloud, Qdrant Cloud, Chroma `CloudClient` | Cloud-hosted. Ticket: coach's machine only. |
| Meilisearch Enterprise | BUSL, not OSI. |
| Elasticsearch / OpenSearch as the product store | Elasticsearch license moved to SSPL / Elastic License; SSPL is **not** OSI. OpenSearch is OSI (Apache-2.0) but is a JVM daemon far above this scale. |
| LanceDB Enterprise SQL | Hosted/enterprise product; Embedded is the local-first shape. |
| Chroma in-memory `Client()` | Ephemeral. |
| Typesense native Windows binary | Install guide has WSL/Docker only. Docker-on-loopback remains a candidate. |
| sqlite-vss | Predecessor; sqlite-vec README calls sqlite-vec the successor. |
| DuckDB `vss` persistence without the experimental flag | First-party: HNSW indexes are in-memory unless `hnsw_enable_experimental_persistence`; WAL recovery incomplete. Brute-force distance at thousands of rows remains available. |
| Remote embedding APIs (`sqlite-rembed`, Qdrant `cloud_inference`) | Leave the machine. FastEmbed / local GGUF / 4B-class models stay in scope. |

## What this does **not** decide

Later tickets own:

- [Grilling: Access methods the data source must support](https://github.com/djsciman/video_transcriber_rag/issues/106) — which of FTS, hop browse, and embeddings are required on day one.
- [Grilling: Physical records and logical indexes](https://github.com/djsciman/video_transcriber_rag/issues/110) — row layout, which columns are FTS vs facet vs playback.
- [Grilling: Lock storage engine, indexes, and playback keys](https://github.com/djsciman/video_transcriber_rag/issues/112) — pick one engine (or one combination).

Facts those tickets can take as given:

- Thousands of rows: SQL btree / `GROUP BY` is a valid hop hierarchy. Dedicated facet engines (Meilisearch, Typesense, Tantivy hierarchical facets, Qdrant `facet()`) are optional convenience.
- Embeddings are optional. An engine without vectors can still be locked if 106/111 leave LLM retrieval off the first spec; adding sqlite-vec / DuckDB `vss` / pgvector / Lance hybrid later is documented.
- Playback is columns (`video_file` basename + time range strings), not a media engine.
- Embedded libraries match the current stdlib HTTP process. Daemons are viable if bound to `127.0.0.1` and given auth (especially Qdrant Docker).
- Chroma’s missing `SECURITY.md` on main is a recorded gap.
- sqlite-vec and DuckDB `vss` persistence are pre-1.0 / experimental; they remain candidates with that label.

## Primary sources

- SQLite FTS5: https://sqlite.org/fts5.html
- SQLite copyright: https://sqlite.org/copyright.html
- SQLite security: https://www.sqlite.org/security.html
- sqlite-vec README, dual license, SECURITY.md: https://github.com/asg017/sqlite-vec
- sqlite-vec PyPI 0.1.9: https://pypi.org/project/sqlite-vec/
- DuckDB FTS: https://duckdb.org/docs/2.0/core_extensions/full_text_search.html
- DuckDB VSS: https://duckdb.org/docs/2.0/core_extensions/vss.html
- DuckDB Python: https://duckdb.org/docs/2.0/clients/python/overview.html
- DuckDB securing: https://duckdb.org/docs/2.0/operations_manual/securing_duckdb/overview.html
- LanceDB FTS: https://docs.lancedb.com/search/full-text-search
- LanceDB hybrid search: https://docs.lancedb.com/enterprise/v1-12-0/search/hybrid-search.md
- Meilisearch install (Windows support table): https://www.meilisearch.com/docs/learn/getting_started/installation
- Meilisearch facets: https://www.meilisearch.com/docs/learn/fine_tuning_results/faceted_search
- Typesense install: https://typesense.org/docs/guide/install-typesense.html
- Typesense LICENSE.txt GPL-3: https://github.com/typesense/typesense/blob/master/LICENSE.txt
- Qdrant local Docker: https://qdrant.tech/documentation/quickstart/
- Qdrant Edge: https://qdrant.tech/documentation/edge/edge-quickstart/
- qdrant-client local mode: https://github.com/qdrant/qdrant-client
- Chroma getting started / clients: https://docs.trychroma.com/docs/overview/getting-started
- PostgreSQL FTS: https://www.postgresql.org/docs/current/textsearch.html
- PostgreSQL licence: https://www.postgresql.org/about/licence/
- pgvector: https://github.com/pgvector/pgvector
- Tantivy: https://github.com/quickwit-oss/tantivy
- USearch: https://github.com/unum-cloud/usearch
- Sibling schema research: issue 102 / `docs/extracted-technique-source/prepared-chapter-json.md` on `research/prepared-chapter-json-issue-102`
- Hop field list: `docs/prepare-llm-prompt.md` §9; Marcelo sample `docs/samples/butterfly-marcelo-s01e01-pare.json`
