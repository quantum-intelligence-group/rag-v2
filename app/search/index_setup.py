"""OpenSearch index initialization and management."""
from opensearchpy import OpenSearch
from app.logging import get_logger
import os

logger = get_logger(__name__)

def get_chunks_mapping():
    """Return the mapping for chunks index."""
    return {
        "properties": {
            "doc_id": {"type": "keyword"},
            "chunk_id": {"type": "keyword"},
            "text": {"type": "text", "analyzer": "standard"},
            "is_table": {"type": "boolean"},
            "page_start": {"type": "integer"},
            "page_end": {"type": "integer"},
            "section_path": {"type": "keyword"},
            "tokens_est": {"type": "integer"},
            "sha256": {"type": "keyword"},
            "lang": {"type": "keyword"},
            "tags": {
                "type": "object",
                "enabled": True,
                "properties": {
                    "tenant": {"type": "keyword"},
                    "source": {"type": "keyword"},
                    "department": {"type": "keyword"},
                    "product": {"type": "keyword"},
                    "project": {"type": "keyword"},
                    "customer": {"type": "keyword"},
                    "confidentiality": {"type": "keyword"},
                    "lifecycle": {"type": "keyword"},
                    "jurisdiction": {"type": "keyword"},
                    "topic": {"type": "keyword"}
                }
            },
            "doc_date": {"type": "date"},
            "effective_date": {"type": "date"},
            "created_at": {"type": "date"},
            "updated_at": {"type": "date"}
        }
    }

def ensure_index_and_alias(client: OpenSearch):
    """
    Ensure chunks index exists with proper mapping and alias.
    Creates versioned index (chunks_v1_000001) and alias (chunks_current).
    """
    index_name = "chunks_v1_000001"
    alias_name = "chunks_current"
    
    try:
        # Check if index exists
        if not client.indices.exists(index=index_name):
            # Create index with mapping
            client.indices.create(
                index=index_name,
                body={
                    "mappings": get_chunks_mapping(),
                    "settings": {
                        "number_of_shards": 2,
                        "number_of_replicas": 0,
                        "index": {
                            "refresh_interval": "1s"
                        }
                    }
                }
            )
            logger.info("created_index", extra={"index": index_name})
        
        # Check if alias exists
        if not client.indices.exists_alias(name=alias_name):
            # Create alias
            client.indices.put_alias(index=index_name, name=alias_name)
            logger.info("created_alias", extra={"alias": alias_name, "index": index_name})
        
        logger.info("index_ready", extra={"index": index_name, "alias": alias_name})
        return True
        
    except Exception as e:
        logger.error("index_setup_failed", extra={"error": str(e)})
        raise