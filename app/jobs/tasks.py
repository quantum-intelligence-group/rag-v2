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
from app.ingest.normalize import (
    normalize_document_text,
    strip_repeating_headers_footers,
    convert_lists_to_markdown
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
            # For now, simulate parsed text content
            raw_text = f"Sample document content for {blob_path}\n\nThis is some text that needs normalization.\n\n1. First item in list\n2. Second item in list\n\n• Bullet point one\n• Bullet point two\n\nRepeating header text\nSome content here\nRepeating header text\nMore content\nRepeating header text\nFinal content"
        
        with stage("normalize", doc_id=doc_id):
            # Apply text normalization pipeline
            # Step 1: Remove repeating headers/footers
            normalized_text = strip_repeating_headers_footers(raw_text)
            
            # Step 2: Convert lists to markdown format
            normalized_text = convert_lists_to_markdown(normalized_text)
            
            # Step 3: General text normalization (whitespace, dehyphenation, etc.)
            normalized_text = normalize_document_text(normalized_text)
            
            logger.info("text_normalized", extra={
                "doc_id": doc_id,
                "original_length": len(raw_text),
                "normalized_length": len(normalized_text)
            })
        
        with stage("chunk", doc_id=doc_id):
            # TODO: Implement proper chunking logic with sentence splitting
            # raw_chunks = chunk_elements(elements)
            # For now, create chunks using normalized text
            chunks = []
            
            # Simple chunking - split normalized text into smaller pieces
            text_parts = normalized_text.split('\n\n')  # Split by paragraphs
            for i, text_part in enumerate(text_parts[:3]):  # Use first 3 parts as chunks
                if text_part.strip():  # Skip empty parts
                    chunk = {
                        "doc_id": doc_id,
                        "chunk_id": f"{i:04d}",  # Zero-padded
                        "text": text_part.strip(),  # Use normalized text
                        "is_table": False,
                        "page_start": i + 1,
                        "page_end": i + 1,
                        "section_path": ["Introduction", "Section A"],
                        "tokens_est": len(text_part.split()) * 1.3,  # Rough token estimate
                        **final_metadata  # Include all metadata in each chunk
                    }
                    chunks.append(chunk)
            
            # Ensure we have at least one chunk
            if not chunks:
                chunk = {
                    "doc_id": doc_id,
                    "chunk_id": "0000",
                    "text": normalized_text[:500] if len(normalized_text) > 500 else normalized_text,
                    "is_table": False,
                    "page_start": 1,
                    "page_end": 1,
                    "section_path": ["Introduction"],
                    "tokens_est": min(len(normalized_text.split()) * 1.3, 150),
                    **final_metadata
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