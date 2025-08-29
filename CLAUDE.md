Purpose: Defines session workflow, coding standards, and logging conventions for the QuickRAG project.

# Invariant Session Loop
0) **Initialize logging** if not already: import `init_logging()` once per process; create `logger = get_logger(__name__)`.

# Instrumentation conventions  <!-- NEW -->
- Use:
  ```python
  from app.logging import get_logger, stage
  logger = get_logger(__name__)
  with stage("parse", doc_id=doc_id, blob_path=blob_path):
      ...

Log counts (chunks, tables) and durations (ms) for each pipeline stage.

Never log secrets; prefer tags/ids over full content.
Coding standards — additions <!-- NEW -->

Every new service function either returns metrics or emits a stage log.

Prefer JSON‑serializable extras in logger.info("msg", extra=...) or via stage(...).
1) **Load planning**: Read `PLANNING.md`.
2) **Scan work**: Read `TASKS.md`.
3) **Pick exactly one** unblocked, atomic task (unless a chain is explicitly grouped).
4) **Propose** plan/diff (files to touch, functions to add, tests) and wait for confirmation if requested.
5) **Implement** minimal diffs; prefer incremental edits over whole‑file rewrites.
6) **Validate**: run or outline tests; update docs if interfaces change.
7) **Mark done**: check off the task in `TASKS.md` with date + artifact note.
8) **Surface follow‑ups**: append new tasks to `TASKS.md` if discovered.

## Mandatory instruction (do not delete)
Always read PLANNING.md at the start of every new conversation, check TASKS.md before starting your work, mark completed tasks to TASKS.md immediately, and add newly discovered tasks to TASKS.md when found.

## Coding standards
- **Language/stack**: Python 3.13, FastAPI, Dramatiq, OpenSearch (opensearch‑py), Milvus (pymilvus), MinIO/Azure SDK.
- **Style**: PEP8; keep functions ≤ ~50 LOC when possible; single responsibility; docstrings on public functions.
- **Testing**: Add/adjust **happy‑path tests** for each new service function. Prefer pure functions in `app/ingest/*` to ease unit tests.
- **Diff hygiene**: Small PR‑sized changes; avoid mass reformatting unless explicitly asked.
- **Determinism**: Deterministic `chunk_id`s (zero‑padded sequence per doc) and `_id = f"{doc_id}:{chunk_id}"` in OpenSearch.
- **Idempotency**: Milvus — delete by `doc_id` before inserts; OpenSearch bulk upsert with `_id`.

## Repository conventions
- **Indexes**: Write to OpenSearch alias `chunks_current`. Use versioned indices behind the alias (`chunks_v1_000001` etc.).
- **Metadata merge precedence**: HTTP body > sidecar `<file>.meta.json` > path inference > defaults.
- **Tables**: Keep as isolated chunks with `is_table=true` and markdown body preserved.
- **Sentence splitting**: Use `syntok` when available; fallback splitter is acceptable in P1.
- **File organization**: 
  - Models go in `app/api/models.py`
  - Routes go in `app/api/routes.py` with multiple routers
  - Keep related functionality grouped in modules (e.g., `app/ingest/metadata.py`)
- **Path pattern**: Extract only `/tenant/dataset/...` from blob paths
- **Required metadata**: Only `tenant` and `dataset` are mandatory tags
- **Doc ID generation**: `{filename_stem}-{sha256[:8]}` when not provided

## Logging & metrics (Phase 1)
- Structured logs per stage: `doc_id`, `blob_path`, durations, counts.
- Emit counters: `ingest_docs_total{status}`, `ingest_chunks_total`.
- Emit histograms: `ingest_stage_seconds{stage=download|parse|chunk|index_os|index_milvus}`.

## Security & safety
- Never embed secrets or credentials in code or logs.
- Enforce container/tenant allowlist for `blob_path` sources. Reject arbitrary URLs.

## Session Summary Template
Date: YYYY‑MM‑DD
Tasks completed:

 <task> — files changed/created: <paths>; notes

Key decisions:

<decision + reason>

Follow‑ups added to TASKS.md:

 <new task>

## Session Summary: 2025-08-28
Tasks completed:
- Milestone 0.1 — Logging Foundation
  - Created `app/logging.py` with JSON formatter, init_logging(), get_logger(), and stage() context manager
  - Wired up logging in `app/main.py` and `app/jobs/worker.py`
  - Created `app/jobs/tasks.py` with instrumented pipeline stages (download, parse, chunk, index_os, index_milvus)
  - LOG_LEVEL env variable support (defaults to INFO)

- Milestone 1 — Ingest API
  - Created `app/search/index_setup.py` for OpenSearch index initialization with versioned index and alias
  - Added models to `app/api/models.py` (IngestRequest, IngestResponse, JobStatus)
  - Implemented routes in `app/api/routes.py` with multiple routers (ingest, search, health)
  - POST /api/ingest endpoint with job queue via Dramatiq
  - GET /api/ingest/{job_id} endpoint for job status
  - Redis job status with 1-hour TTL
  - Updated `app/main.py` with lifespan handler for index initialization

Key decisions:
- Used minimal, dependency-free JSON logging approach as specified
- stage() context manager emits start/ok/error logs with duration_ms
- Quieted uvicorn access logs to WARNING level to reduce noise
- Used logging.info() with extra={} for structured fields
- Organized API with multiple routers per service domain (Option A)
- Used Redis for transient job status (1hr TTL) - sufficient for MVP
- Wrapped all ingest stages in single try block for clean error handling
- Used FastAPI lifespan context manager instead of deprecated on_event

Files changed/created:
- Created: `app/logging.py`, `app/jobs/tasks.py`, `app/search/index_setup.py`
- Modified: `app/main.py`, `app/jobs/worker.py`
- Created: `app/api/models.py`, `app/api/routes.py`

Follow-ups added to TASKS.md:
- None (completed all Milestone 0.1 and Milestone 1 tasks)


## Quick prompts to use with Claude Code
- “Please read `PLANNING.md`, `CLAUDE.md`, and `TASKS.md`. Then complete the first unblocked task in `Milestone 1 — Ingest API`.”
- “Add a session summary to `CLAUDE.md` summarizing the work completed.”