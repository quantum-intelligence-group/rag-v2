"""Job status management utilities."""
import redis
import json
import os
from datetime import datetime, timezone
from typing import Optional
from app.logging import get_logger
from app.api.models import JobStatus

logger = get_logger(__name__)

# Redis client for job status
redis_client = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://redis:6379/0"),
    decode_responses=True
)

def set_job_status(job_id: str, status: str, **kwargs):
    """Store job status in Redis with 1 hour TTL."""
    data = {
        "job_id": job_id,
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **kwargs
    }
    
    # Get existing data to preserve created_at
    existing = redis_client.get(f"job:{job_id}")
    if existing:
        existing_data = json.loads(existing)
        data["created_at"] = existing_data.get("created_at")
    else:
        data["created_at"] = data["updated_at"]
    
    redis_client.setex(
        f"job:{job_id}",
        3600,  # 1 hour TTL
        json.dumps(data)
    )
    logger.info("job_status_updated", extra={"job_id": job_id, "status": status})

def get_job_status(job_id: str) -> Optional[JobStatus]:
    """Retrieve job status from Redis."""
    data = redis_client.get(f"job:{job_id}")
    if data:
        return JobStatus(**json.loads(data))
    return None