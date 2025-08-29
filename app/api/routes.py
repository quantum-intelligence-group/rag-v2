"""API routes for ingest and search operations."""
from fastapi import APIRouter, HTTPException
import uuid
import time
from app.logging import get_logger
from app.api.models import IngestRequest, IngestResponse, JobStatus, SearchRequest, SearchResponse, SearchResult
from app.jobs.tasks import ingest_blob
from app.jobs.status import set_job_status, get_job_status
from app.ingest.normalize import normalize_query

logger = get_logger(__name__)

# Create routers for different services
ingest_router = APIRouter(prefix="/api/ingest", tags=["ingest"])
search_router = APIRouter(prefix="/api/search", tags=["search"])
health_router = APIRouter(prefix="/api/health", tags=["health"])


# Ingest endpoints
@ingest_router.post("/", response_model=IngestResponse)
async def ingest(request: IngestRequest):
    """
    Submit a document for ingestion.
    
    Returns a job_id to track the async processing status.
    """
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Validate blob_path (basic check - enhance with allowlist later)
    if not request.blob_path:
        raise HTTPException(status_code=400, detail="blob_path is required")
    
    # TODO: Add blob_path allowlist validation for security
    
    try:
        # Set initial job status
        set_job_status(job_id, "pending", doc_id=request.doc_id)
        
        # Enqueue the task
        ingest_blob.send(
            job_id=job_id,
            blob_path=request.blob_path,
            doc_id=request.doc_id,
            tags=request.tags
        )
        
        logger.info("ingest_job_queued", extra={
            "job_id": job_id,
            "blob_path": request.blob_path,
            "doc_id": request.doc_id
        })
        
        return IngestResponse(
            job_id=job_id,
            status="pending",
            message=f"Job {job_id} queued for processing"
        )
        
    except Exception as e:
        logger.error("ingest_submission_failed", extra={
            "job_id": job_id,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail="Failed to submit ingest job")

@ingest_router.get("/{job_id}", response_model=JobStatus)
async def get_job(job_id: str):
    """
    Get the status of an ingest job.
    
    Returns job status, counts, and any error information.
    """
    status = get_job_status(job_id)
    
    if not status:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    return status

# Search endpoints
@search_router.post("/", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Search documents using normalized query.
    
    This is a placeholder that demonstrates query normalization.
    Full BM25 + vector search will be implemented in Phase 2.
    """
    start_time = time.time()
    
    # Normalize the query
    normalized_query = normalize_query(request.query)
    
    if not normalized_query:
        raise HTTPException(status_code=400, detail="Query cannot be empty after normalization")
    
    logger.info("search_request", extra={
        "original_query": request.query,
        "normalized_query": normalized_query,
        "tags": request.tags,
        "limit": request.limit
    })
    
    # TODO: Implement actual search using OpenSearch + Milvus
    # For now, return mock results to demonstrate the normalized query
    mock_results = [
        SearchResult(
            doc_id="example-doc-12345678",
            chunk_id="0001",
            text=f"This is a mock search result for query: '{normalized_query}'",
            score=0.85,
            page_start=1,
            page_end=1,
            section_path=["Introduction"],
            is_table=False
        )
    ]
    
    search_time_ms = (time.time() - start_time) * 1000
    
    return SearchResponse(
        query=request.query,
        normalized_query=normalized_query,
        results=mock_results,
        total_results=len(mock_results),
        search_time_ms=search_time_ms
    )

# Health endpoints
@health_router.get("/ready")
async def ready_check():
    """Check if service is ready to handle requests."""
    # TODO: Check Redis, OpenSearch, Milvus connections
    return {"status": "ready"}

@health_router.get("/live")
async def liveness_check():
    """Simple liveness check."""
    return {"status": "alive"}