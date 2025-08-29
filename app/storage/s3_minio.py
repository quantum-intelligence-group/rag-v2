"""S3/MinIO storage client implementation."""
import os
from typing import List, Optional
from datetime import datetime
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from app.storage.base import StorageClient
from app.logging import get_logger

logger = get_logger(__name__)

class S3MinioClient(StorageClient):
    """Storage client for S3-compatible storage (MinIO, AWS S3)."""
    
    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
        use_ssl: bool = False
    ):
        """
        Initialize S3/MinIO client.
        
        Args:
            endpoint_url: S3 endpoint URL (for MinIO)
            access_key: Access key ID
            secret_key: Secret access key
            bucket_name: Default bucket name
            use_ssl: Whether to use SSL
        """
        # Get from env if not provided
        self.endpoint_url = endpoint_url or os.getenv("MINIO_ENDPOINT", "http://minio:9000")
        self.access_key = access_key or os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = secret_key or os.getenv("MINIO_SECRET_KEY", "minioadmin")
        self.bucket_name = bucket_name or os.getenv("MINIO_BUCKET_NAME", "documents")
        
        # Create S3 client
        self.client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            use_ssl=use_ssl,
            verify=False  # For MinIO with self-signed certs
        )
        
        # Ensure bucket exists
        self._ensure_bucket()
        
        logger.info("s3_client_initialized", extra={
            "endpoint": self.endpoint_url,
            "bucket": self.bucket_name
        })
    
    def _ensure_bucket(self):
        """Create bucket if it doesn't exist."""
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = int(e.response["Error"]["Code"])
            if error_code == 404:
                # Bucket doesn't exist, create it
                self.client.create_bucket(Bucket=self.bucket_name)
                logger.info("bucket_created", extra={"bucket": self.bucket_name})
            else:
                logger.error("bucket_check_failed", extra={"error": str(e)})
                raise
    
    def download(self, blob_path: str) -> bytes:
        """Download blob content from S3/MinIO."""
        try:
            response = self.client.get_object(
                Bucket=self.bucket_name,
                Key=blob_path
            )
            content = response["Body"].read()
            
            logger.info("blob_downloaded", extra={
                "blob_path": blob_path,
                "size": len(content)
            })
            
            return content
            
        except ClientError as e:
            error_code = int(e.response["Error"]["Code"])
            if error_code == 404:
                raise FileNotFoundError(f"Blob not found: {blob_path}")
            elif error_code == 403:
                raise PermissionError(f"Access denied: {blob_path}")
            else:
                logger.error("download_failed", extra={
                    "blob_path": blob_path,
                    "error": str(e)
                })
                raise
    
    def upload(self, blob_path: str, content: bytes, metadata: Optional[dict] = None) -> bool:
        """
        Upload content to S3/MinIO.
        
        Note: metadata here is blob-level metadata (stored in S3),
        NOT document metadata (which goes to OpenSearch/Milvus).
        """
        try:
            # Prepare S3 metadata
            s3_metadata = {}
            if metadata:
                # S3 metadata keys must be strings
                s3_metadata = {str(k): str(v) for k, v in metadata.items()}
            
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=blob_path,
                Body=content,
                Metadata=s3_metadata
            )
            
            logger.info("blob_uploaded", extra={
                "blob_path": blob_path,
                "size": len(content)
            })
            
            return True
            
        except ClientError as e:
            logger.error("upload_failed", extra={
                "blob_path": blob_path,
                "error": str(e)
            })
            if e.response["Error"]["Code"] == "AccessDenied":
                raise PermissionError(f"Access denied: {blob_path}")
            raise
    
    def exists(self, blob_path: str) -> bool:
        """Check if blob exists in S3/MinIO."""
        try:
            self.client.head_object(
                Bucket=self.bucket_name,
                Key=blob_path
            )
            return True
        except ClientError as e:
            error_code = int(e.response["Error"]["Code"])
            if error_code == 404:
                return False
            else:
                logger.error("exists_check_failed", extra={
                    "blob_path": blob_path,
                    "error": str(e)
                })
                raise
    
    def list_blobs(self, prefix: str = "", max_results: int = 1000) -> List[str]:
        """List blobs in S3/MinIO."""
        try:
            paginator = self.client.get_paginator("list_objects_v2")
            
            params = {
                "Bucket": self.bucket_name,
                "MaxKeys": max_results
            }
            if prefix:
                params["Prefix"] = prefix
            
            blob_paths = []
            for page in paginator.paginate(**params):
                if "Contents" in page:
                    for obj in page["Contents"]:
                        blob_paths.append(obj["Key"])
                        if len(blob_paths) >= max_results:
                            break
                
                if len(blob_paths) >= max_results:
                    break
            
            logger.info("blobs_listed", extra={
                "prefix": prefix,
                "count": len(blob_paths)
            })
            
            return blob_paths
            
        except ClientError as e:
            logger.error("list_failed", extra={
                "prefix": prefix,
                "error": str(e)
            })
            raise
    
    def delete(self, blob_path: str) -> bool:
        """Delete blob from S3/MinIO."""
        try:
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=blob_path
            )
            
            logger.info("blob_deleted", extra={"blob_path": blob_path})
            return True
            
        except ClientError as e:
            error_code = int(e.response["Error"]["Code"])
            if error_code == 404:
                raise FileNotFoundError(f"Blob not found: {blob_path}")
            else:
                logger.error("delete_failed", extra={
                    "blob_path": blob_path,
                    "error": str(e)
                })
                raise
    
    def get_blob_info(self, blob_path: str) -> dict:
        """Get metadata about a blob in S3/MinIO."""
        try:
            response = self.client.head_object(
                Bucket=self.bucket_name,
                Key=blob_path
            )
            
            return {
                "size": response.get("ContentLength", 0),
                "last_modified": response.get("LastModified", datetime.now()).isoformat(),
                "content_type": response.get("ContentType", "application/octet-stream"),
                "etag": response.get("ETag", "").strip('"'),
                "metadata": response.get("Metadata", {})  # Blob-level metadata
            }
            
        except ClientError as e:
            error_code = int(e.response["Error"]["Code"])
            if error_code == 404:
                raise FileNotFoundError(f"Blob not found: {blob_path}")
            else:
                logger.error("info_failed", extra={
                    "blob_path": blob_path,
                    "error": str(e)
                })
                raise