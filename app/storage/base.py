"""Base storage client abstract class.

IMPORTANT: Storage Metadata vs Document Metadata
=================================================

1. Storage Metadata (Blob-level)
   - Attached to blobs in S3/Azure
   - Used for: storage management, access control, audit
   - Examples: upload_time, content_type, user_id
   - NOT indexed in OpenSearch/Milvus

2. Document Metadata (Application-level)  
   - Stored with chunks in OpenSearch/Milvus
   - Used for: search, filtering, retrieval
   - Examples: doc_id, tenant, dataset, confidentiality, tags
   - Rich business metadata for search

The storage layer is agnostic to business logic.
Tenant/dataset validation happens in the ingest layer, not here.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from app.logging import get_logger

logger = get_logger(__name__)

class StorageClient(ABC):
    """Abstract base class for storage clients - pure storage operations only."""
    
    @abstractmethod
    def download(self, blob_path: str) -> bytes:
        """
        Download blob content from storage.
        
        Args:
            blob_path: Path to the blob (e.g., "tenant1/dataset1/file.pdf")
            
        Returns:
            Raw bytes of the blob content
            
        Raises:
            FileNotFoundError: If blob doesn't exist
            PermissionError: If access is denied
        """
        pass
    
    @abstractmethod
    def upload(self, blob_path: str, content: bytes, metadata: Optional[dict] = None) -> bool:
        """
        Upload content to storage.
        
        Args:
            blob_path: Path where to store the blob
            content: Raw bytes to upload
            metadata: Optional metadata to attach to blob
            
        Returns:
            True if successful
            
        Raises:
            PermissionError: If access is denied
        """
        pass
    
    @abstractmethod
    def exists(self, blob_path: str) -> bool:
        """
        Check if a blob exists.
        
        Args:
            blob_path: Path to check
            
        Returns:
            True if blob exists, False otherwise
        """
        pass
    
    @abstractmethod
    def list_blobs(self, prefix: str = "", max_results: int = 1000) -> List[str]:
        """
        List blobs with optional prefix filter.
        
        Args:
            prefix: Optional prefix to filter blobs
            max_results: Maximum number of results to return
            
        Returns:
            List of blob paths
        """
        pass
    
    @abstractmethod
    def delete(self, blob_path: str) -> bool:
        """
        Delete a blob from storage.
        
        Args:
            blob_path: Path to the blob to delete
            
        Returns:
            True if deleted successfully
            
        Raises:
            FileNotFoundError: If blob doesn't exist
        """
        pass
    
    @abstractmethod
    def get_blob_info(self, blob_path: str) -> dict:
        """
        Get metadata about a blob.
        
        Args:
            blob_path: Path to the blob
            
        Returns:
            Dictionary with blob metadata (size, last_modified, content_type, etc.)
            
        Raises:
            FileNotFoundError: If blob doesn't exist
        """
        pass