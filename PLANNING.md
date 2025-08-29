# QuickRAG — Planning

## Vision (implementation lens)
Stateless services that ingest documents from blob storage, normalize and chunk them, and index into BM25 (OpenSearch) and vectors (Milvus). Emphasis on reproducible chunking, rich metadata, and faithful citations (page span + section path).

## Architecture (text diagram)
[Client/UI or script]
   └── POST /api/ingest {blob_path, doc_id?, tags?}
        └── API (FastAPI) ──> Dramatiq/Redis ──> Worker
                                   │
                                   ├─ Download blob (MinIO dev / Azure prod)
                                   ├─ Parse (unstructured: PDF/DOCX/HTML)
                                   ├─ Normalize (whitespace, de‑hyphenate, boilerplate strip)
                                   ├─ Chunk (sentence windows; 800–1200 tok; 15% overlap; tables isolated)
                                   ├─ Index BM25 (OpenSearch alias: `chunks_current`)
                                   └─ Vectors (Milvus `chunks_v1`, dim=768; P1 vectors=zero stubs)

Dependencies (dev):
- OpenSearch 2.13.0 (BM25)
- Milvus 2.6.0 + etcd + MinIO
- Redis (Dramatiq broker)
- Python 3.13 containers (api/worker)

## Technology stack & rationale
- **FastAPI** for simple APIs and Pydantic models.
- **Dramatiq + Redis** for at‑least‑once background jobs.
- **unstructured** partitioners for PDF/DOCX/HTML (single‑process simplicity).
- **OpenSearch** for keyword search & filtering by `tags.*`.
- **Milvus** for vector similarity (COSINE, HNSW); dim=768 to fit BGE‑small later.
- **syntok** for light, good sentence splitting without model downloads.

## Data models (authoritative)
**Document (logical)**
- `doc_id`, `filename`, `blob_path`, `content_type`, `language`, `doc_date?`, `effective_date?`,
- `created_at`, `updated_at`, `sha256`, `pages?`, `tags{tenant, source, department, product, project, customer, confidentiality, lifecycle, jurisdiction, topic}`,
- Optional: `doc_version`, `source_kind`, `origin_etag`, `ingest_run_id`.

**Chunk (indexable)**
- `doc_id`, `chunk_id` (zero‑padded per doc), `text`, `is_table`, `page_start`, `page_end`,
- `section_path[]`, `tokens_est`, `sha256`, `lang`, `tags{...}`,
- Optional: `chunk_summary`, `headings[]`, `origin_offsets{start_char,end_char}`.

## Index design
- **OpenSearch**
  - Alias: `chunks_current` → versioned index (e.g., `chunks_v1_000001`).
  - `_id = "{doc_id}:{chunk_id}"` (deterministic; safe on retries).
  - Mapping includes `tags` (enabled object), dates, page spans, `section_path` (keyword).
- **Milvus**
  - Collection `chunks_v1`: fields `id (auto)`, `doc_id (VARCHAR 128)`, `chunk_id (VARCHAR 128)`, `text (VARCHAR 8192)`, `vector (FLOAT_VECTOR, dim=768)`.
  - Index: HNSW (COSINE). **Delete by `doc_id`** before insert to preserve idempotency.

## Ingest pathway (Phase 1)
1. **Trigger**: `POST /api/ingest` with `{blob_path, doc_id?, tags?}`.
2. **Merge metadata**: HTTP body > sidecar `<file>.meta.json` > path inference > defaults.
3. **Parse** with `unstructured` (`partition_pdf|docx|html`).
4. **Normalize**: collapse whitespace; de‑hyphenate line wraps; strip repeated header/footer; convert lists to markdown.
5. **Chunk**:
   - Narrative: sentence split (prefer `syntok`), window to ~1000 tokens, 15% overlap at boundaries.
   - Tables: separate chunks; `is_table=true`.
   - Carry `section_path` via nearest Title/Heading ancestry.
6. **Index**: OpenSearch bulk (alias `chunks_current`), then Milvus insert (vectors=zero stubs).
7. **Status**: Track `job_id` in Redis (status, error, counts).

## Security
- Allowlist containers/prefixes for `blob_path`. Reject external URLs.
- Tag‑based access control will be handled at query/UI layer later; ensure tags present from day 1.

## Operational SLOs (dev)
- Ingest p95 ≤ 120s for 10–20p PDFs.
- Index parity: OpenSearch count == Milvus count per job.
- Error rate < 2% across ingest jobs (retriable).

## Required tools (dev)
- Docker/Compose; curl/httpie; OpenSearch client; pymilvus; syntok; unstructured; dramatiq; redis client.

## Open questions
- Do we backfill embeddings for existing chunks automatically when we switch to real embeddings?
- Which jurisdictions/tags should be mandatory for compliance docs?
- Do we need Event Grid auto‑ingest in P1.1?

## Logging & metrics foundation  <!-- IMPLEMENTED -->
- **Logger:** single module `app/logging.py` exporting `init_logging()`, `get_logger()`, and `stage(name)` context manager.
- **Format:** one line **JSON** to STDOUT. Fields: `ts, level, logger, msg, job_id, doc_id, blob_path, stage, duration_ms, counts`.
- **Usage rule:** every new function that touches the pipeline wraps its critical section with `stage("...")`.
- **Metrics:** counters `ingest_docs_total{status}`, `ingest_chunks_total`; histograms `ingest_stage_seconds{stage}`. (Prom exporter in Phase 2.)

## Retrieval pipeline (Phase 2+)  <!-- NEW -->
1) **Normalize** the query; optional multi‑query (2–4 paraphrases) or HyDE later.
2) **Run in parallel:**
   - **BM25 (OpenSearch)**: top 50 with tag filters.
   - **Vector (Milvus)**: top 50 using 768‑dim embeddings.
3) **Fuse with RRF** (k≈60). 
4) **Optional rerank** with `bge-reranker-base`.
5) **Answer** via small LLM with strict “answer only from context, cite pages” instruction.
6) **Cache** the final answer + inputs.

## Caches (Phase 2)  <!-- NEW -->
- **Answer cache** (1–7 days TTL).
- **Embedding cache** keyed by `sha256(normalized_text)`.
- **BM25 result cache** (30–120 min TTL).

## Future components (containers)  <!-- NEW -->
- **vLLM or llama.cpp** for small LLM serving (Phase 4). (tbd probably sticking to using llm server for now openai, anthropic, groq, etc.)
- **Prometheus + Grafana** or **OTel collector + Tempo/Loki** (Phase 2) (centralized store exists. just need to be able to make sure logs are being sent to where the need to be setn.)


## Current Implementation Status  <!-- NEW 2025-08-28 -->
### Completed Components:
- **Logging**: JSON structured logging with stage() context manager (`app/logging.py`)
- **API Routes**: Multi-router architecture (ingest, search, health) in `app/api/routes.py`
- **Models**: Pydantic models in `app/api/models.py`
- **Job Status**: Redis-based with 1-hour TTL
- **OpenSearch Setup**: Index initialization with versioned index + alias (`app/search/index_setup.py`)
- **Metadata Pipeline**: Complete merge precedence, validation, SHA256-based doc_id (`app/ingest/metadata.py`)
- **Idempotent Indexing**: OpenSearch bulk upsert, Milvus delete-before-insert (`app/search/indexing.py`)

### Design Decisions Made:
- **Simplified path pattern**: Only extract `/tenant/dataset/...` (not full hierarchy)
- **Required tags**: Only `tenant` and `dataset` (minimal MVP)
- **Sidecar files**: Optional JSON files for convenience
- **Redis for job status**: No PostgreSQL needed for MVP
- **Router organization**: Multiple routers in single file (Option A)

## Decision log
- 2025‑08‑28: Use alias `chunks_current` for BM25 index versioning.
- 2025‑08‑28: Keep vectors as zero stubs in P1; target BGE‑small‑en‑v1.5 in P2.
- 2025‑08‑28: Simplified metadata to tenant/dataset only; sidecar files optional.
- 2025‑08‑28: Redis sufficient for job status (no PostgreSQL for MVP).
- 2025‑08‑28: Use multi-router pattern in single routes.py file.
