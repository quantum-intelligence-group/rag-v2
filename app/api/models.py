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

# Search models
class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query text")
    tags: Optional[Dict[str, str]] = Field(default_factory=dict, description="Filter tags (tenant, dataset, etc.)")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results")

class SearchResult(BaseModel):
    doc_id: str
    chunk_id: str
    text: str
    score: float
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    section_path: Optional[list] = None
    is_table: bool = False

class SearchResponse(BaseModel):
    query: str
    normalized_query: str
    results: list[SearchResult]
    total_results: int
    search_time_ms: float