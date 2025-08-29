"""Storage module with factory for different storage backends."""
import os
from typing import Optional
from app.storage.base import StorageClient
from app.storage.s3_minio import S3MinioClient
from app.storage.azure_blob import AzureBlobClient
from app.logging import get_logger

logger = get_logger(__name__)

def get_storage_client(storage_type: Optional[str] = None) -> StorageClient:
    """
    Factory function to get the appropriate storage client.
    
    Args:
        storage_type: Type of storage ('azure', 'minio', 's3'). 
                     Defaults to env var STORAGE_TYPE or 'minio'.
    
    Returns:
        StorageClient instance
        
    Raises:
        ValueError: If storage type is unknown
    """
    storage_type = storage_type or os.getenv("STORAGE_TYPE", "minio")
    storage_type = storage_type.lower()
    
    logger.info("creating_storage_client", extra={"type": storage_type})
    
    if storage_type == "azure":
        return AzureBlobClient()
    elif storage_type in ("minio", "s3"):
        return S3MinioClient()
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")

# Export commonly used items
__all__ = [
    "StorageClient",
    "S3MinioClient", 
    "AzureBlobClient",
    "get_storage_client"
]