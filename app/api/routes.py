"""API routes for ingest and search operations."""
from fastapi import APIRouter, HTTPException
import uuid
from app.logging import get_logger
from app.api.models import IngestRequest, IngestResponse, JobStatus
from app.jobs.tasks import ingest_blob
from app.jobs.status import set_job_status, get_job_status

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

# Search endpoints (placeholder for now)
@search_router.post("/hybrid")
async def hybrid_search():
    """Hybrid BM25 + vector search (to be implemented)."""
    return {"message": "Search endpoint coming in Phase 2"}

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