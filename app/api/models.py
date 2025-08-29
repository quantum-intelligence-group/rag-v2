"""API request/response models."""
from pydantic import BaseModel, Field
from typing import Dict, Optional

# Ingest models
class IngestRequest(BaseModel):
    blob_path: str = Field(..., description="Path to blob in storage")
    doc_id: Optional[str] = Field(None, description="Document ID (auto-generated if not provided)")
    tags: Optional[Dict[str, str]] = Field(default_factory=dict, description="Metadata tags")

class IngestResponse(BaseModel):
    job_id: str
    status: str
    message: str

class JobStatus(BaseModel):
    job_id: str
    status: str  # pending, processing, done, failed
    doc_id: Optional[str] = None
    error: Optional[str] = None
    counts: Optional[Dict[str, int]] = None
    created_at: str
    updated_at: str