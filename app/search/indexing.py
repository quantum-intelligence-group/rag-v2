"""Indexing operations for OpenSearch and Milvus with idempotency."""
from typing import List, Dict
from opensearchpy import OpenSearch, helpers
from pymilvus import Collection, connections
from app.logging import get_logger, stage
import json

logger = get_logger(__name__)

def bulk_index_opensearch(
    client: OpenSearch,
    chunks: List[Dict],
    index_alias: str = "chunks_current"
) -> Dict:
    """
    Bulk index chunks to OpenSearch with upsert semantics.
    Uses deterministic _id for idempotency.
    """
    if not chunks:
        logger.warning("no_chunks_to_index")
        return {"indexed": 0, "errors": []}
    
    # Prepare bulk operations
    operations = []
    for chunk in chunks:
        # Deterministic ID for idempotency
        chunk_id = f"{chunk['doc_id']}:{chunk['chunk_id']}"
        
        operations.append({
            "_index": index_alias,
            "_id": chunk_id,
            "_source": chunk
        })
    
    # Execute bulk operation
    try:
        response = helpers.bulk(
            client,
            operations,
            raise_on_error=False,
            raise_on_exception=False
        )
        
        success_count = response[0]
        errors = response[1]
        
        logger.info("opensearch_bulk_complete", extra={
            "indexed": success_count,
            "error_count": len(errors),
            "total_chunks": len(chunks)
        })
        
        return {"indexed": success_count, "errors": errors}
        
    except Exception as e:
        logger.error("opensearch_bulk_failed", extra={"error": str(e)})
        raise

def delete_and_insert_milvus(
    collection_name: str,
    doc_id: str,
    chunks: List[Dict]
) -> Dict:
    """
    Delete existing vectors for doc_id, then insert new ones.
    Ensures idempotency for document re-ingestion.
    """
    try:
        # Connect to collection
        collection = Collection(collection_name)
        
        # Delete existing vectors for this doc_id
        delete_expr = f'doc_id == "{doc_id}"'
        with stage("milvus_delete", doc_id=doc_id):
            result = collection.delete(delete_expr)
            deleted_count = result.delete_count if hasattr(result, 'delete_count') else 0
            logger.info("milvus_deleted", extra={
                "doc_id": doc_id,
                "deleted_count": deleted_count
            })
        
        if not chunks:
            return {"inserted": 0, "deleted": deleted_count}
        
        # Prepare data for insertion
        doc_ids = [chunk["doc_id"] for chunk in chunks]
        chunk_ids = [chunk["chunk_id"] for chunk in chunks]
        texts = [chunk["text"][:8192] for chunk in chunks]  # Milvus VARCHAR limit
        
        # For now, use zero vectors (will be replaced with real embeddings later)
        vectors = [[0.0] * 768 for _ in chunks]  # 768-dim zero vectors
        
        # Insert new vectors
        with stage("milvus_insert", doc_id=doc_id, count=len(chunks)):
            data = [
                doc_ids,
                chunk_ids,
                texts,
                vectors
            ]
            
            result = collection.insert(data)
            
            # Flush to make data immediately searchable
            collection.flush()
            
            logger.info("milvus_inserted", extra={
                "doc_id": doc_id,
                "inserted_count": len(result.primary_keys)
            })
            
            return {
                "inserted": len(result.primary_keys),
                "deleted": deleted_count
            }
            
    except Exception as e:
        logger.error("milvus_operation_failed", extra={
            "doc_id": doc_id,
            "error": str(e)
        })
        raise

def verify_parity(
    opensearch_client: OpenSearch,
    collection_name: str,
    doc_id: str,
    index_alias: str = "chunks_current"
) -> bool:
    """
    Verify that OpenSearch and Milvus have the same number of chunks for a doc_id.
    """
    try:
        # Count in OpenSearch
        os_query = {
            "query": {
                "term": {"doc_id": doc_id}
            }
        }
        os_response = opensearch_client.count(index=index_alias, body=os_query)
        os_count = os_response["count"]
        
        # Count in Milvus
        collection = Collection(collection_name)
        collection.load()
        
        expr = f'doc_id == "{doc_id}"'
        milvus_results = collection.query(
            expr=expr,
            output_fields=["doc_id"],
            limit=10000
        )
        milvus_count = len(milvus_results)
        
        # Compare
        is_matching = os_count == milvus_count
        
        logger.info("parity_check", extra={
            "doc_id": doc_id,
            "opensearch_count": os_count,
            "milvus_count": milvus_count,
            "parity": is_matching
        })
        
        return is_matching
        
    except Exception as e:
        logger.error("parity_check_failed", extra={
            "doc_id": doc_id,
            "error": str(e)
        })
        return False