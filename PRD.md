# QuickRAG @ Quantum Intelligence
A fast, precise, and auditable Retrieval‑Augmented Generation system for internal and customer-facing knowledge.

## Problem
QI’s knowledge lives in PDFs, DOCX, HTML, and scattered sources. Finding accurate, citable answers is slow and error‑prone. We need a system that can ingest documents quickly, chunk them well, index for both keyword and vector retrieval, and return answers with faithful citations.

## Who it's for
- **Engineers / Data Scientists** — need specs, designs, and API details quickly.
- **Solutions / Sales** — need pricing, product capabilities, and contractual terms with citations.
- **Ops / Compliance / Legal** — need policy clauses by jurisdiction/effective dates.

## User stories (MVP)
- As a user, I can **drop a file** into blob storage and call `POST /api/ingest` so it is **queryable within minutes**.
- As a user, I can filter and retrieve chunks by **tags** (tenant, product, project, confidentiality, lifecycle).
- As a user, I get **citations** with **page spans** and **section paths** for every chunk returned.
- As an operator, I can **re‑ingest** a document idempotently without duplicating chunks.
- As an operator, I can see **ingestion metrics** and per‑stage timings.

## Scope (Phase 1)
- Pipeline: **Blob → Metadata → Parse → Normalize → Chunk → Index (OpenSearch + Milvus)**.
- Parsers: `unstructured` for PDF/DOCX/HTML. **No OCR** in P1.
- Chunking: sentence‑aware windows (~800–1200 tokens) with 15% overlap; **tables isolated**.
- Indexing: BM25 in OpenSearch (`chunks_current` alias) + vector stubs in Milvus (dim=768; zeros for now).
- Idempotency: `doc_id` + `sha256` + deterministic `chunk_id`s.
- Metadata: **Required**: tenant, dataset. **Optional**: department, confidentiality, doc_type, language, source_system.
- Path pattern: Simple `/tenant/dataset/...` extraction only.

## Out of scope (Phase 1)
- OCR/image tables; advanced main‑content extraction for noisy HTML; dedupe across near‑identical docs; semantic chunking; real embeddings (stub used).

## Success criteria (Phase 1)
- Ingest of a typical 10–20 page PDF completes **≤ 120s p95** end‑to‑end on dev hardware.
- OpenSearch and Milvus contain **matching chunk counts** after ingest.
- Each chunk records **`section_path`** and **`page_start/page_end`**.
- Pipeline is **idempotent**, safe to retry; **status API** returns meaningful progress.
- Basic metrics: **doc/chunk counters** and **per‑stage histograms**.

## Future (Phase 2+)
- Real embeddings (**bge‑small‑en‑v1.5**) + hybrid retrieval; rerankers; semantic chunking; table summarization; OCR; Event Grid auto‑ingest; HTML readability; dashboard for docs/jobs.

## Operational priorities  <!-- NEW -->
1) **Logging & metrics FIRST**: structured JSON logs + per‑stage timings are required before new features.
2) **Idempotent pipeline**: safe retries end‑to‑end.
3) **Faithful citations**: every chunk keeps `section_path` and `page_start/page_end`.

## Roadmap snapshot (high‑level)  <!-- NEW -->
- **Phase 0 (done):** Scaffold containers & skeleton API/worker.
- **Phase 1:** Ingest → Parse → Normalize → Chunk → Index (BM25 + vector stubs).
- **Phase 2:** Retrieval stack: **parallel BM25 + vector**; **RRF** to merge; optional **reranker**.
- **Phase 3:** **Caching:** answer cache, embedding cache, BM25 result cache (Redis/Dragonfly).
- **Phase 4:** **Answering with a small LLM** (Llama‑3.1‑8B / Qwen2.5‑7B); strict cite‑or‑abstain prompt.
- **Phase 5:** **Evaluation & telemetry** (Ragas; p95 per stage; click/rating loop).
- **Phase 6:** **Hardening & tenancy** (authZ via tags; doc versioning; PII scrub; rate limits).

## Retrieval & answering plan (Phase 2+)  <!-- NEW -->
- **Parallel retrieval:** BM25 (OpenSearch) **and** vectors (Milvus).
- **Fusion:** **Reciprocal Rank Fusion (RRF)** to merge lists; simple, strong default.
- **Rerank (optional):** `bge-reranker-base` to keep top 8–15 chunks.
- **Answering:** small local LLM with context window; “cite or abstain” guardrail.
- **Embeddings target:** `bge-small-en-v1.5` (CPU OK, GPU better).

## Caching plan (Phase 2)  <!-- NEW -->
- **Answer cache:** `ans:{hash(query+docset)} → {answer,citations,ts}`.
- **Embedding cache:** `emb:{model}:{sha256(text)} → vector`.
- **BM25 result cache:** `bm25:{index}:{hash(query)} → topN`.

## Success criteria (Phase 1) — additions  <!-- NEW -->
- **Logging present across all stages**; each job emits `download|parse|chunk|index_os|index_milvus` durations.
- **Dash‑readiness:** Logs are JSON and compatible with Prometheus/Grafana or OpenTelemetry exporters.


## Changelog
- **2025‑08‑28** — Initial PRD for Phase 1 based on Phase 0 scaffold.
- **2025-08-28** — Completed Milestone 0.1 (Logging) and Milestones 1-2 (Ingest API, Metadata).

## Current Implementation Status
### Completed (as of 2025-08-28):
- JSON structured logging with stage() context manager
- Ingest API endpoints (POST /api/ingest, GET /api/ingest/{job_id})
- Redis job status tracking (1-hour TTL)
- OpenSearch index setup with versioned index + alias
- Metadata pipeline with validation and merge precedence
- Idempotent indexing strategies for both stores

### Architecture Decisions:
- No PostgreSQL: Redis sufficient for transient job status
- Simplified metadata: Only tenant/dataset required (not full hierarchy)
- Optional sidecar files: .meta.json files for convenience but not required
- Multi-router pattern: Organized by domain (ingest, search, health)
- Doc ID strategy: SHA256-based for determinism
