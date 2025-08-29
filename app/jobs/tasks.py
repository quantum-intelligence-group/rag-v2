import dramatiq
from app.logging import get_logger, stage
from app.jobs.status import set_job_status
from app.ingest.metadata import (
    load_sidecar,
    infer_from_path, 
    validate_metadata,
    merge_metadata,
    enrich_metadata
)
from app.storage import get_storage_client

logger = get_logger(__name__)

@dramatiq.actor(max_retries=2)
def ingest_blob(job_id: str, blob_path: str, doc_id: str | None = None, tags: dict | None = None):
    """
    Main ingest task that processes a document from blob storage.
    
    Stages:
    1. download - fetch from blob storage
    2. parse - extract text/structure
    3. chunk - split into indexable chunks
    4. index_os - index to OpenSearch
    5. index_milvus - index to Milvus
    """
    tags = tags or {}
    
    # Update job status to processing
    set_job_status(job_id, "processing", doc_id=doc_id)
    
    try:
        with stage("download", job_id=job_id, blob_path=blob_path):
            # Download blob from storage
            storage_client = get_storage_client()
            content_bytes = storage_client.download(blob_path)
            logger.info("blob_downloaded", extra={
                "job_id": job_id,
                "blob_path": blob_path,
                "size": len(content_bytes)
            })
            
        with stage("metadata", job_id=job_id):
            # Load metadata from various sources
            sidecar_tags = load_sidecar(blob_path)
            path_tags = infer_from_path(blob_path)
            
            # Merge with precedence: HTTP > sidecar > path > defaults
            merged_tags = merge_metadata(
                http_tags=tags,
                sidecar_tags=sidecar_tags,
                path_tags=path_tags,
                defaults={"language": "en"}
            )
            
            # Validate required fields
            validated_tags = validate_metadata(merged_tags, blob_path)
            
            # Add derived metadata (doc_id, sha256, etc.)
            final_metadata = enrich_metadata(validated_tags, blob_path, content_bytes, doc_id)
            doc_id = final_metadata["doc_id"]  # Use computed doc_id
        
        with stage("parse", doc_id=doc_id or "", blob_path=blob_path):
            # TODO: Implement parsing with unstructured
            # elements = parse_document(content, content_type)
            pass
        
        with stage("chunk", doc_id=doc_id):
            # TODO: Implement chunking logic
            # raw_chunks = chunk_elements(elements)
            # For now, create dummy chunks with metadata
            chunks = []
            for i in range(3):  # Create 3 dummy chunks
                chunk = {
                    "doc_id": doc_id,
                    "chunk_id": f"{i:04d}",  # Zero-padded
                    "text": f"Dummy chunk {i} content",
                    "is_table": False,
                    "page_start": i + 1,
                    "page_end": i + 1,
                    "section_path": ["Introduction", "Section A"],
                    "tokens_est": 150,
                    **final_metadata  # Include all metadata in each chunk
                }
                chunks.append(chunk)
        
        with stage("index_os", doc_id=doc_id):
            # TODO: Use real OpenSearch client
            # from app.search.opensearch_client import client
            # from app.search.indexing import bulk_index_opensearch
            # result = bulk_index_opensearch(client, chunks)
            pass
        
        with stage("index_milvus", doc_id=doc_id):
            # TODO: Use real Milvus connection
            # from app.search.indexing import delete_and_insert_milvus
            # result = delete_and_insert_milvus("chunks_v1", doc_id, chunks)
            pass
        
        # All stages completed successfully
        set_job_status(job_id, "done", doc_id=doc_id, counts={"chunks": len(chunks)})
        
        logger.info("ingest_done", extra={
            "job_id": job_id,
            "doc_id": doc_id,
            "counts": {"chunks": len(chunks)}
        })
        
    except Exception as e:
        # Update job status to failed
        set_job_status(job_id, "failed", doc_id=doc_id, error=str(e))
        logger.error("ingest_failed", extra={
            "job_id": job_id,
            "doc_id": doc_id,
            "error": str(e)
        })
        raise  # Re-raise for Dramatiq retry logic