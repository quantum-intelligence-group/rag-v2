# QuickRAG Tasks

Each task is atomic (one Claude iteration). When complete, mark `[x]` with date and a brief artifact note.

---

## Milestone 0 — Scaffold (Completed)
- [x] Docker Compose stack for API, Worker, Redis, Milvus (2.6.0), MinIO, OpenSearch (2.13.0) — **2025‑08‑28** (added `compose.yml`)
- [x] FastAPI + Dramatiq skeleton, package layout (`app/*`) — **2025‑08‑28**
- [x] Basic clients for OpenSearch/Milvus, storage adapters (Azure/MinIO) — **2025‑08‑28**

## Milestone 0.1 — Logging Foundation (Do this FIRST)  <!-- NEW -->
- [x] Create `app/logging.py` with JSON formatter, `init_logging()`, `get_logger()`, and `stage(name)` context manager. — **2025-08-28** (created app/logging.py)
- [x] Call `init_logging()` in API startup (`app/main.py`) and worker bootstrap (`app/jobs/worker.py`). — **2025-08-28**
- [x] Instrument `app/jobs/tasks.py` stages with `stage("download|parse|chunk|index_os|index_milvus")` and emit counts. — **2025-08-28** (created app/jobs/tasks.py with stages)
- [x] Add LOG_LEVEL env (default INFO) and ensure logs flow to STDOUT (Docker). — **2025-08-28** (logging.py reads LOG_LEVEL env)
- [ ] (Phase 2) Expose Prometheus metrics endpoint and add dashboards (ingest p95, stage durations, error rates).

---

## Milestone 1 — Ingest API
- [x] **Ensure OpenSearch index + alias**: create versioned index `chunks_v1_000001` with mapping; alias `chunks_current`; idempotent on startup. — **2025-08-28** (created app/search/index_setup.py)
- [x] `POST /api/ingest` endpoint (validate input, generate `job_id`, enqueue Dramatiq). — **2025-08-28** (app/api/routes.py)
- [x] `GET /api/ingest/{job_id}` (reads Redis status; returns `{status, counts, doc_id, error?}`). — **2025-08-28** (app/api/routes.py)
- [x] Status persistence in Redis with TTL; include stage timings. — **2025-08-28** (1hr TTL in Redis)

## Milestone 2 — Metadata & Idempotency
- [x] Sidecar loader: read `<blob>.meta.json` if present. — **2025-08-28** (app/ingest/metadata.py)
- [x] Path inference (tenant/dataset pattern). — **2025-08-28** (simplified to tenant/dataset only)
- [x] Merge precedence: HTTP > sidecar > path > defaults. — **2025-08-28** (merge_metadata function)
- [x] Compute `sha256` of original bytes; derive default `doc_id` if missing (`<stem>-<sha8>`). — **2025-08-28** (compute_doc_id function)
- [x] OpenSearch bulk with `_id = "{doc_id}:{chunk_id}"` (upsert‑safe). — **2025-08-28** (app/search/indexing.py)
- [x] Milvus **delete‑by‑expr** for `doc_id` before inserts. — **2025-08-28** (delete_and_insert_milvus function)

## Milestone 2.5 — Storage Abstraction Layer
- [x] Implement base `StorageClient` abstract class in `app/storage/base.py` — **2025-08-28** (removed business logic, pure storage)
- [x] Implement `S3MinioClient` in `app/storage/s3_minio.py` for local development — **2025-08-28** 
- [x] Implement `AzureBlobClient` in `app/storage/azure_blob.py` for production — **2025-08-28**
- [x] Create `get_storage_client()` factory function with STORAGE_TYPE env variable — **2025-08-28** (app/storage/__init__.py)
- [x] Add storage configuration to .env file (connection strings, bucket names) — **2025-08-28**
- [ ] Test storage client with both MinIO and Azure emulator

## Milestone 2.6 — Integration Test (Test what we have so far!)
- [x] Wire up storage client in `app/jobs/tasks.py` download stage — **2025-08-28**
- [x] Create test script to upload a test file to MinIO/Azure — **2025-08-28** (upload_test_file.py)
- [x] Test E2E flow with dummy content: upload → ingest → check job status — **2025-08-28** (test_e2e.py)
- [ ] Verify metadata extraction from path (tenant/dataset pattern)
- [ ] Verify OpenSearch index creation and dummy chunks indexed
- [ ] Verify Milvus connection and delete-before-insert works
- [ ] Test job status transitions: pending → processing → done/failed
- [ ] Add docker-compose up test to ensure all services start correctly

## Milestone 3 — Parsing & Normalization
- [ ] `unstructured` partitioners for PDF/DOCX/HTML (fast path), preserve element type & page numbers.
- [ ] Normalize document text: collapse whitespace, de‑hyphenate line wraps, strip repeating headers/footers, list→markdown, and removing emojis.
- [X] Normalize Query text: collapse whitespace, de‑hyphenate line wraps, strip repeating headers/footers, list→markdown, and removing emojis. app/api/ingest/normalize.py
- [ ] Convert tables to Markdown; emit separate blocks with `is_table=true`.

## Milestone 4 — Chunking v1
- [ ] Add `syntok` sentence splitter; fallback to simple splitter if unavailable.
- [ ] Window builder: ~1000 tokens target with **15% overlap**.
- [ ] Do not split inside tables; carry `section_path` from nearest headings.
- [ ] Deterministic zero‑padded `chunk_id` per doc.
- [ ] Per‑chunk `sha256` (normalized text), `tokens_est`, `page_start/page_end`.

## Milestone 5 — Indexing & Parity
- [ ] Bulk index chunks to OpenSearch alias `chunks_current`; `refresh` policy chosen for throughput vs immediacy.
- [ ] Ensure Milvus collection `chunks_v1` with HNSW(COSINE), dim=768; insert vectors as **zeros** in P1.
- [ ] Verify parity: OpenSearch doc count equals Milvus row count per `doc_id`.

## Milestone 6 — Metrics & Logging
- [ ] Structured logs per stage with durations and counts.
- [ ] Counters: `ingest_docs_total{status}`, `ingest_chunks_total`.
- [ ] Histograms: `ingest_stage_seconds{stage}` for `download|parse|chunk|index_os|index_milvus`.
- [ ] **Note:** basic JSON logs are delivered in **Milestone 0.1**; this milestone covers exporters/dashboards.

## Milestone 7 — Acceptance (Phase 1)
- [ ] E2E ingest of PDF/DOCX/HTML each produces ≥1 chunk.
- [ ] `/api/ingest` returns `job_id`; `/api/ingest/{job_id}` reaches `done`.
- [ ] Chunks contain `section_path` and `page_start/page_end`.
- [ ] OpenSearch and Milvus counts match for the ingested `doc_id`.
- [ ] p95 ingest time ≤ 120s on dev box for a ~10–20p PDF.

## Milestone 8 — Retrieval + Answering (Phase 2)  <!-- NEW -->
- [ ] Implement BM25 searching as standalone endpoint
- [ ] Implement vector searching as standalone endpoint
- [ ] Implement **parallel BM25 + vector** retrieval with tag filters.
- [ ] Add **RRF** fusion; tune `k`.
- [ ] Optional **reranker** (`bge-reranker-base`) for top‑K.
- [ ] LLM (grok / openai) answering with “cite or abstain” prompt template.

## Milestone 10 — Evaluation & Hardening (Phase 2+)  <!-- NEW -->
- [ ] Ragas eval; collect online feedback (thumbs/clicks).
- [ ] AuthZ via tags/tenant; doc versioning + soft delete.
- [ ] PII/secret scrub; rate limiting.
---

## Backlog (Phase 2+)
- [ ] Plug real embeddings (`bge-small-en-v1.5`) via `sentence-transformers` or `fastembed`; backfill vectors.
- [ ] Hybrid retrieval + reranker; semantic chunking (semantic‑text‑splitter).
- [ ] HTML readability pre‑pass for noisy pages.
- [ ] OCR pipeline for scanned PDFs; table structure extraction improvements.
- [ ] Event Grid auto‑ingest for Azure Blob creates.
- [ ] Dashboard: docs, jobs, metrics, and search UX.

---

## Done
(Record finished tasks here with date and artifact notes.)
