# Local CPU embedding models for extracted-technique vectors

Research for [Research: Local CPU embedding models for extracted-technique vectors](https://github.com/djsciman/video_transcriber_rag/issues/123). Performed 2026-11-25. Parent: [Extracted-technique data source for the curated store](https://github.com/djsciman/video_transcriber_rag/issues/101).

**Question:** which local CPU embedding models fit this machine and this corpus, so ingest and sentence-find can share one model?

This note compares candidates. It does **not** lock a model. A later grilling picks one. Storage-engine lock is a later ticket; this note only reports vector dimensions and float32 byte sizes so an engine can consume them.

Coach-facing screens say extracted index later. This research is about the embedder. One findable row is one **extracted technique**: a corpus JSON object in a chapter `techniques` array. The vector is of `named_move`, `technique_steps`, and `main_ideas` concatenated.

## Constraints (locked; do not reopen)

From [Grilling: Access methods the data source must support](https://github.com/djsciman/video_transcriber_rag/issues/106#issuecomment-7168539532):

- Local **CPU** embedding model. No GPU. No cloud embeddings API. No xAI Collections.
- Ingest: embed each extracted technique from `named_move`, `technique_steps`, and `main_ideas`. No chat per row.
- Find: embed the filter chat call's English find-string (not the coach's typed sentence).
- Same model both times. Vectors stay on the coach's machine next to the row.
- Scale: **5378** extracted-technique rows (measured 2026-11-25).
- Hardware: Intel i9-9980HK (8 cores / 16 threads), 31.7 GB RAM. The GTX 1650 is unused for this. Windows. Python 3.12 via `py -3`.
- Do not lock a storage engine. sqlite-vec 0.1.9, DuckDB, LanceDB, pgvector, and others may consume vectors.

## Practical Windows CPU path

The path that actually imported and ran here is **FastEmbed 0.9.1 + onnxruntime 1.32.0 CPU**, not PyTorch.

- `pip install fastembed` pulled `onnxruntime` (CPU). PyPI `onnxruntime` 1.32.0 is MIT, requires Python >=3.11, classifiers include 3.12 and Windows, and ships `onnxruntime-1.32.0-cp312-cp312-win_amd64.whl` (~16.7 MB).
- FastEmbed 0.9.1 is Apache-2.0 (`license_expression` on [PyPI](https://pypi.org/project/fastembed/0.9.1/)), requires Python >=3.10, classifiers include 3.12. Default `TextEmbedding()` model is `BAAI/bge-small-en-v1.5`. It uses ONNX Runtime and does not download a CUDA torch stack.
- This throwaway venv (`py -3.12.10`): `import fastembed` and `import onnxruntime` succeeded. `ort.get_available_providers()` returned `['AzureExecutionProvider', 'CPUExecutionProvider']` (no CUDA). Sessions were created with `providers=["CPUExecutionProvider"]` and `CUDA_VISIBLE_DEVICES=""`.
- `import torch` and `import sentence_transformers` raised `ModuleNotFoundError`. That is expected: they were not installed. Pulling them would bring a large torch wheel; this ticket prefers the CPU-first ONNX path.

GGUF / llama.cpp embedding models exist, but they are not the practical path on this chassis next to a working onnxruntime CPU wheel. They were not timed.

## Candidate comparison

Legend: **ONNX size** is FastEmbed `size_in_GB` from [Supported Models](https://qdrant.github.io/fastembed/examples/Supported_Models/). **Params** are Hugging Face safetensors totals. **Retrieval** numbers are owner-reported MTEB/BEIR figures (task names in the column). FastEmbed 0.9.1 ships some models as Qdrant ONNX ports (sometimes quantized, suffix `-onnx-Q`).

| Candidate | HF / package id | Params / ONNX size | License | English retrieval (owner numbers) | Dim | Max seq | CPU here |
|---|---|---|---|---|---|---|---|
| MiniLM-L6 | `sentence-transformers/all-MiniLM-L6-v2` (FastEmbed downloads `Qdrant/all-MiniLM-L6-v2-onnx`) | 22.7M; 0.090 GB ONNX | Apache-2.0 ([HF `license:apache-2.0`](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)) | Snowflake table **MTEB Retrieval Score (NDCG @ 10) 41.95**. Own card: **ArguAna** NDCG 50.17 (MTEB v1.12.75). Card: default truncate **256 word pieces** | 384 | ST default 256 (`sentence_bert_config.json`); tokenizer 512 | **Yes.** Imported via FastEmbed. Timed below |
| MiniLM-L12 | `sentence-transformers/all-MiniLM-L12-v2` | 33.4M | Apache-2.0 (HF card) | Own card: **ArguAna** NDCG 47.13 (MTEB v1.38.3). **384-d, not 768-d** | 384 | ST default 256 word pieces | Not in FastEmbed 0.9.1 dense list (only L6 and `paraphrase-multilingual-MiniLM-L12-v2`). Not timed |
| BGE-small | `BAAI/bge-small-en-v1.5` (FastEmbed: `Qdrant/bge-small-en-v1.5-onnx-Q`) | 33.4M; 0.067 GB ONNX | MIT ([FlagEmbedding LICENSE](https://github.com/FlagOpen/FlagEmbedding/blob/master/LICENSE); HF `license=mit`) | BGE README MTEB **Average (56) 62.17**, **Retrieval (15) 51.68**. Snowflake same Retrieval 51.68 | 384 | 512 (`max_position_embeddings`) | **Yes.** Timed below. FastEmbed default model |
| Arctic-xs | `Snowflake/snowflake-arctic-embed-xs` | 22.6M; 0.090 GB ONNX | Apache-2.0 (model card License section; HF `license=apache-2.0`) | Snowflake **MTEB Retrieval Score (NDCG @ 10) 50.15**. Based on MiniLM-L6 | 384 | 512 (`model_max_length` / usage `max_length=512`) | **Yes.** Timed below |
| Arctic-s | `Snowflake/snowflake-arctic-embed-s` | 33.2M; 0.130 GB ONNX | Apache-2.0 (HF card) | Snowflake **MTEB Retrieval Score (NDCG @ 10) 51.98**. Based on e5-small-unsupervised | 384 | 512 | In FastEmbed list. Not timed (xs already shows the 22M MiniLM-class cost) |
| E5-small | `intfloat/e5-small-v2` | 33.4M | MIT (HF `license=mit`) | Snowflake **MTEB Retrieval Score (NDCG @ 10) 49.04**. BGE table lists e5-small-v2 as 384-d / 512 seq. Card requires `query:` / `passage:` prefixes | 384 | 512 (card: truncated to at most 512 tokens) | **Not in FastEmbed 0.9.1 supported list.** English-only. Not timed |
| Multilingual-E5-small | `intfloat/multilingual-e5-small` | 118M (0.1B on card) | MIT (HF `license=mit`) | Card **Mr. TyDi Avg MRR@10 64.4**; English column **54.5**. 12 layers, 384-d. Requires `query:` / `passage:` even for non-English | 384 | 512 | FastEmbed 0.9.1 lists `intfloat/multilingual-e5-large` only. README shows `TextEmbedding.add_custom_model` for this id with `onnx/model.onnx`. Not timed |
| BGE-base (768-d cost) | `BAAI/bge-base-en-v1.5` (FastEmbed: `Qdrant/bge-base-en-v1.5-onnx-Q`) | 109.5M; 0.210 GB ONNX | MIT (same FlagEmbedding LICENSE) | BGE README MTEB **Average (56) 63.55**, **Retrieval (15) 53.25**. Snowflake Retrieval 53.25 | 768 | 512 | **Yes.** Timed below. Load + ingest much slower than 384-d |
| E5-base (768-d, not timed) | `intfloat/e5-base-v2` | 109.5M | MIT (HF card) | BGE README **Average (56) 61.5**, **Retrieval (15) 50.29**. Prefixes required | 768 | 512 | Not in FastEmbed 0.9.1 list. Documented for cost vs 384-d only |

Query / passage prefixes (same model must be used at ingest and find):

- MiniLM: none.
- BGE v1.5: optional query instruction `Represent this sentence for searching relevant passages:`. Passages never get the instruction. v1.5 "no instruction only has a slight degradation."
- E5 family: required `query:` on the find-string and `passage:` on ingest text, or quality drops.
- Arctic: query prefix `Represent this sentence for searching relevant passages:` (sentence-transformers `prompt_name="query"`). Documents unprefixed.

A grilling that picks E5 or Arctic must lock those prefixes on both paths. MiniLM has no prefix contract.

## Measured on this machine (2026-11-25)

Hardware re-checked: Intel Core i9-9980HK @ 2.40 GHz, 8 cores / 16 threads, 31.7 GB RAM (16.7 GB free at the RAM query). Python 3.12.10 (`py -3`). FastEmbed 0.9.1, onnxruntime 1.32.0, `CPUExecutionProvider` only.

Texts:

- Sample concat from `docs/samples/butterfly-marcelo-s01e01-pare.json` (five extracted-technique objects; Butterfly sweep first row 1430 chars of `named_move` + `technique_steps` + `main_ideas`).
- Ingest corpus: **5378 live varied** extracted-technique concatenations from `C:\Users\dumbo\Documents\GitHub\bjj_transcripts\library` (5373 unique). Corpus was not modified.
- Find-string (English filter-chat stand-in): `no-gi butterfly sweep from bottom: deep underhook, push the elbow in, scoop the opponent off the ground, turn onto the shoulder, keep the lifting knee pointed out`.

All four models ran in **one process**, sequentially. `rss_after_ingest_mb` is **process-lifetime RSS**, so MiniLM's 4128 MB is the cleanest single-model peak; later rows accumulate leftover sessions and numpy arrays. Load seconds for MiniLM / bge-small / arctic-xs include first Hugging Face download into `%TEMP%\fastembed_cache`. bge-base load 380 s is first download of the 0.210 GB ONNX plus init.

| Model | Load (s) | Find 1 string (s) | Ingest 5378 (s) | Dim | float32 bytes for 5378 | RSS after load (MB, delta) | RSS after ingest (MB, cumulative) |
|---|---|---|---|---|---|---|---|
| `sentence-transformers/all-MiniLM-L6-v2` | 9.676 | 0.0068 | **160.333** | 384 | 8,260,608 (~7.9 MiB) | 208.8 (delta 123.6) | 4128.3 |
| `BAAI/bge-small-en-v1.5` | 7.946 | 0.0147 | 455.387 | 384 | 8,260,608 | 256.1 (delta 120.2) | 6028.4 |
| `snowflake/snowflake-arctic-embed-xs` | 9.879 | 0.0081 | 212.047 | 384 | 8,260,608 | 243.3 (delta 101.2) | 8960.2 |
| `BAAI/bge-base-en-v1.5` | 380.338 | 0.0274 | 1437.742 | 768 | 16,521,216 (~15.8 MiB) | 529.0 (delta 383.6) | 12001.7 |

Throughput on this CPU (5378 / ingest_s): MiniLM-L6 ~33.5 rows/s; arctic-xs ~25.4; bge-small ~11.8; bge-base ~3.7.

Useful finding the ticket asked for: a 384-d MiniLM-class model (`all-MiniLM-L6-v2`, Apache-2.0) embeds 5378 live extracted-technique texts in **160 seconds** on this CPU, with a one-string find in **7 ms**, and 5378 float32 vectors occupy **8.3 MB**. Arctic-xs (also 384-d, Apache-2.0, owner Retrieval 50.15 vs MiniLM 41.95) took 212 s. BGE-small (MIT, Retrieval 51.68) took 455 s on the quantized FastEmbed ONNX. The 768-d BGE-base class is ~9x slower to ingest than MiniLM-L6 and doubles stored bytes; it still fits RAM.

5378 x 384-d float32 is small enough that brute-force cosine on the coach's machine is enough. ANN is optional. That matches sibling [Research: Local storage engines for search, hierarchy, and LLM retrieval](https://github.com/djsciman/video_transcriber_rag/issues/103).

## What still fits

Several local CPU models fit this chassis and this 5378-row grain. MiniLM-L6, arctic-xs, and bge-small all:

- Import on Python 3.12 Windows via FastEmbed + onnxruntime CPU.
- Produce 384-d vectors (~8.3 MB for the whole corpus).
- Embed one find-string in well under 20 ms after load.
- Finish a full ingest in a few minutes on this i9.

768-d bge-base also ran on CPU, at a much higher wall-clock cost. E5-small-v2 is a quality peer on paper but is not in FastEmbed's built-in list; it needs a custom ONNX hook and required prefixes. MiniLM-L12 is 384-d (not a 768-d upgrade) and is absent from FastEmbed 0.9.1's dense list.

No model is locked.

## What is NOT locked

- Which model ingest and find will share.
- Query/passage prefix policy (forced if E5 or Arctic is picked).
- Storage engine (sqlite-vec, DuckDB, LanceDB, pgvector, ...).
- Quantized vs full-precision ONNX (FastEmbed used `-onnx-Q` for the BGE ports).
- Product names on coach-facing screens.

## Out of scope

- OpenAI / Voyage / Cohere / Gemini / xAI embedding APIs.
- GPU-only models and the unused GTX 1650.
- 7B+ embedding LLMs.
- Closing [Research: Local CPU embedding models for extracted-technique vectors](https://github.com/djsciman/video_transcriber_rag/issues/123) or editing the parent map.

## Sources

- Live corpus walk 2026-11-25: 5378 concatenations from `C:\Users\dumbo\Documents\GitHub\bjj_transcripts\library`; sample `docs/samples/butterfly-marcelo-s01e01-pare.json`
- Timing: throwaway venv FastEmbed 0.9.1 + onnxruntime 1.32.0, `CPUExecutionProvider`, `CUDA_VISIBLE_DEVICES=""`
- FastEmbed: [PyPI 0.9.1](https://pypi.org/project/fastembed/0.9.1/) (Apache-2.0, Python 3.10-3.14 classifiers), [Supported Models](https://qdrant.github.io/fastembed/examples/Supported_Models/), README default model and `add_custom_model`
- onnxruntime: [PyPI 1.32.0](https://pypi.org/project/onnxruntime/1.32.0/) MIT, `onnxruntime-1.32.0-cp312-cp312-win_amd64.whl`
- MiniLM-L6: [model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) Apache-2.0, 22.7M, 384-d, 256 word-piece truncate, ArguAna 50.17; `sentence_bert_config.json` `max_seq_length` 256
- MiniLM-L12: [model card](https://huggingface.co/sentence-transformers/all-MiniLM-L12-v2) Apache-2.0, 33.4M, 384-d, ArguAna 47.13
- BGE: [BAAI/bge-small-en-v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5) README MTEB Average/Retrieval table; [FlagEmbedding LICENSE](https://github.com/FlagOpen/FlagEmbedding/blob/master/LICENSE) MIT; `config.json` `hidden_size` / `max_position_embeddings`
- Arctic: [snowflake-arctic-embed-xs](https://huggingface.co/Snowflake/snowflake-arctic-embed-xs) size table (xs 50.15 / MiniLM 41.95 / s 51.98 / bge-small 51.68 / e5-small-v2 49.04 / bge-base 53.25), Apache-2 license section, query prefix in usage
- E5: [e5-small-v2](https://huggingface.co/intfloat/e5-small-v2) 33.4M, 384-d, 512 tokens, MIT, required prefixes; [multilingual-e5-small](https://huggingface.co/intfloat/multilingual-e5-small) Mr. TyDi table
- HF API `cardData.license` / `safetensors.total` for param counts (2026-11-25)
- Sibling engines note on `research/local-storage-engines-issue-103`
