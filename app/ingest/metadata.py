"""Metadata extraction, validation, and merging."""
import hashlib
import json
import re
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, timezone
from app.logging import get_logger

logger = get_logger(__name__)

# Required and optional tags
REQUIRED_TAGS = {"tenant", "dataset"}
OPTIONAL_TAGS = {
    "department", 
    "confidentiality",  # public/internal/confidential
    "doc_type",         # contract/report/email/etc
    "language",         # en/es/fr
    "source_system",    # originating system
}

# Valid values for certain tags
VALID_CONFIDENTIALITY = {None, "public", "internal", "confidential"}

def load_sidecar(blob_path: str, storage_client=None) -> Dict:
    """
    Load metadata from sidecar file (e.g., doc.pdf.meta.json).
    Returns empty dict if sidecar doesn't exist.
    """
    sidecar_path = f"{blob_path}.meta.json"
    
    try:
        # TODO: Use actual storage client when implemented
        # For now, return empty dict
        logger.info("checking_sidecar", extra={"sidecar_path": sidecar_path})
        return {}
    except Exception as e:
        logger.warning("sidecar_load_failed", extra={
            "sidecar_path": sidecar_path,
            "error": str(e)
        })
        return {}

def infer_from_path(blob_path: str) -> Dict:
    """
    Extract metadata from path structure.
    Expected pattern: /{tenant}/{dataset}/...
    """
    tags = {}
    
    # Simple pattern: /tenant/dataset/rest/of/path
    pattern = r"^/?(?P<tenant>[^/]+)/(?P<dataset>[^/]+)/"
    match = re.match(pattern, blob_path)
    
    if match:
        tags["tenant"] = match.group("tenant").lower().strip()
        tags["dataset"] = match.group("dataset").lower().strip()
        logger.info("path_inference_success", extra=tags)
    else:
        logger.warning("path_inference_failed", extra={"blob_path": blob_path})
    
    return tags

def validate_metadata(tags: Dict, blob_path: str) -> Dict:
    """
    Validate and sanitize metadata tags.
    Ensures required fields are present and values are valid.
    """
    # Make a copy to avoid modifying input
    validated = dict(tags)
    
    # Check required fields
    missing = REQUIRED_TAGS - set(validated.keys())
    if missing:
        # Try to fill from path
        path_tags = infer_from_path(blob_path)
        for field in missing:
            if field in path_tags:
                validated[field] = path_tags[field]
        
        # Check again
        missing = REQUIRED_TAGS - set(validated.keys())
        if missing:
            raise ValueError(f"Required tags missing: {missing}")
    
    # Validate specific fields
    if validated.get("confidentiality") not in VALID_CONFIDENTIALITY:
        raise ValueError(f"Invalid confidentiality: {validated.get('confidentiality')}")
    
    # Sanitize tenant and dataset
    validated["tenant"] = validated["tenant"].lower().strip()
    validated["dataset"] = validated["dataset"].lower().strip()
    
    # Remove any unknown tags (optional - we might want to keep them)
    # validated = {k: v for k, v in validated.items() 
    #              if k in REQUIRED_TAGS | OPTIONAL_TAGS}
    
    logger.info("metadata_validated", extra={"tags": validated})
    return validated

def merge_metadata(
    http_tags: Optional[Dict],
    sidecar_tags: Optional[Dict],
    path_tags: Optional[Dict],
    defaults: Optional[Dict] = None
) -> Dict:
    """
    Merge metadata from multiple sources with precedence:
    HTTP > sidecar > path > defaults
    """
    merged = {}
    
    # Start with defaults
    if defaults:
        merged.update(defaults)
    
    # Apply in precedence order (lowest to highest)
    if path_tags:
        merged.update(path_tags)
    
    if sidecar_tags:
        merged.update(sidecar_tags)
    
    if http_tags:
        merged.update(http_tags)
    
    logger.info("metadata_merged", extra={"merged_tags": merged})
    return merged

def compute_doc_id(blob_path: str, content_bytes: bytes, doc_id: Optional[str] = None) -> tuple[str, str]:
    """
    Generate document ID from content SHA256.
    Returns (doc_id, sha256_hash).
    
    If doc_id provided, use it; otherwise generate from filename + hash.
    """
    # Compute SHA256
    sha256_hash = hashlib.sha256(content_bytes).hexdigest()
    
    if doc_id:
        # Use provided doc_id
        return doc_id, sha256_hash
    
    # Generate doc_id from filename + hash
    filename = Path(blob_path).stem  # filename without extension
    doc_id = f"{filename}-{sha256_hash[:8]}"
    
    logger.info("doc_id_computed", extra={
        "doc_id": doc_id,
        "sha256": sha256_hash,
        "blob_path": blob_path
    })
    
    return doc_id, sha256_hash

def enrich_metadata(tags: Dict, blob_path: str, content_bytes: bytes, doc_id: Optional[str] = None) -> Dict:
    """
    Add derived metadata to tags.
    Includes doc_id, sha256, file info, timestamps.
    """
    enriched = dict(tags)
    
    # Compute doc_id and SHA256
    computed_doc_id, sha256_hash = compute_doc_id(blob_path, content_bytes, doc_id)
    
    # Add derived fields
    enriched.update({
        "doc_id": computed_doc_id,
        "sha256": sha256_hash,
        "blob_path": blob_path,
        "filename": Path(blob_path).name,
        "file_type": Path(blob_path).suffix.lower().lstrip("."),
        "file_size": len(content_bytes),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    })
    
    return enriched