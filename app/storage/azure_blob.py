"""Azure Blob Storage client implementation."""
import os
from typing import List, Optional
from datetime import datetime
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError
from app.storage.base import StorageClient
from app.logging import get_logger

logger = get_logger(__name__)

class AzureBlobClient(StorageClient):
    """Storage client for Azure Blob Storage."""
    
    def __init__(
        self,
        connection_string: Optional[str] = None,
        container_name: Optional[str] = None,
        account_url: Optional[str] = None,
        credential: Optional[str] = None
    ):
        """
        Initialize Azure Blob Storage client.
        
        Args:
            connection_string: Azure Storage connection string
            container_name: Default container name
            account_url: Alternative to connection string (requires credential)
            credential: Azure credential (SAS token, key, or DefaultAzureCredential)
        """
        # Get from env if not provided
        self.connection_string = connection_string or os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        self.container_name = container_name or os.getenv("AZURE_CONTAINER_NAME", "documents")
        
        # Initialize client
        if self.connection_string:
            self.blob_service_client = BlobServiceClient.from_connection_string(
                self.connection_string
            )
        elif account_url and credential:
            self.blob_service_client = BlobServiceClient(
                account_url=account_url,
                credential=credential
            )
        else:
            raise ValueError("Either connection_string or (account_url + credential) required")
        
        # Get container client
        self.container_client = self.blob_service_client.get_container_client(
            self.container_name
        )
        
        # Ensure container exists
        self._ensure_container()
        
        logger.info("azure_client_initialized", extra={
            "container": self.container_name
        })
    
    def _ensure_container(self):
        """Create container if it doesn't exist."""
        try:
            self.container_client.get_container_properties()
        except ResourceNotFoundError:
            # Container doesn't exist, create it
            self.container_client.create_container()
            logger.info("container_created", extra={"container": self.container_name})
    
    def download(self, blob_path: str) -> bytes:
        """Download blob content from Azure."""
        try:
            blob_client = self.container_client.get_blob_client(blob_path)
            content = blob_client.download_blob().readall()
            
            logger.info("blob_downloaded", extra={
                "blob_path": blob_path,
                "size": len(content)
            })
            
            return content
            
        except ResourceNotFoundError:
            raise FileNotFoundError(f"Blob not found: {blob_path}")
        except Exception as e:
            logger.error("download_failed", extra={
                "blob_path": blob_path,
                "error": str(e)
            })
            raise
    
    def upload(self, blob_path: str, content: bytes, metadata: Optional[dict] = None) -> bool:
        """
        Upload content to Azure Blob Storage.
        
        Note: metadata here is blob-level metadata (stored in Azure),
        NOT document metadata (which goes to OpenSearch/Milvus).
        """
        try:
            blob_client = self.container_client.get_blob_client(blob_path)
            
            # Azure metadata must have string values
            azure_metadata = {}
            if metadata:
                azure_metadata = {str(k): str(v) for k, v in metadata.items()}
            
            # Upload with overwrite
            blob_client.upload_blob(
                content,
                metadata=azure_metadata,
                overwrite=True
            )
            
            logger.info("blob_uploaded", extra={
                "blob_path": blob_path,
                "size": len(content)
            })
            
            return True
            
        except Exception as e:
            logger.error("upload_failed", extra={
                "blob_path": blob_path,
                "error": str(e)
            })
            raise
    
    def exists(self, blob_path: str) -> bool:
        """Check if blob exists in Azure."""
        try:
            blob_client = self.container_client.get_blob_client(blob_path)
            blob_client.get_blob_properties()
            return True
        except ResourceNotFoundError:
            return False
        except Exception as e:
            logger.error("exists_check_failed", extra={
                "blob_path": blob_path,
                "error": str(e)
            })
            raise
    
    def list_blobs(self, prefix: str = "", max_results: int = 1000) -> List[str]:
        """List blobs in Azure container."""
        try:
            blob_paths = []
            
            # List blobs with optional prefix
            blobs = self.container_client.list_blobs(
                name_starts_with=prefix if prefix else None
            )
            
            for blob in blobs:
                blob_paths.append(blob.name)
                if len(blob_paths) >= max_results:
                    break
            
            logger.info("blobs_listed", extra={
                "prefix": prefix,
                "count": len(blob_paths)
            })
            
            return blob_paths
            
        except Exception as e:
            logger.error("list_failed", extra={
                "prefix": prefix,
                "error": str(e)
            })
            raise
    
    def delete(self, blob_path: str) -> bool:
        """Delete blob from Azure."""
        try:
            blob_client = self.container_client.get_blob_client(blob_path)
            blob_client.delete_blob()
            
            logger.info("blob_deleted", extra={"blob_path": blob_path})
            return True
            
        except ResourceNotFoundError:
            raise FileNotFoundError(f"Blob not found: {blob_path}")
        except Exception as e:
            logger.error("delete_failed", extra={
                "blob_path": blob_path,
                "error": str(e)
            })
            raise
    
    def get_blob_info(self, blob_path: str) -> dict:
        """Get metadata about a blob in Azure."""
        try:
            blob_client = self.container_client.get_blob_client(blob_path)
            properties = blob_client.get_blob_properties()
            
            return {
                "size": properties.size,
                "last_modified": properties.last_modified.isoformat() if properties.last_modified else None,
                "content_type": properties.content_settings.content_type if properties.content_settings else "application/octet-stream",
                "etag": properties.etag,
                "metadata": properties.metadata or {}  # Blob-level metadata
            }
            
        except ResourceNotFoundError:
            raise FileNotFoundError(f"Blob not found: {blob_path}")
        except Exception as e:
            logger.error("info_failed", extra={
                "blob_path": blob_path,
                "error": str(e)
            })
            raise