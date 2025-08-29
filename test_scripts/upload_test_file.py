#!/usr/bin/env python3
"""Upload a test file to storage for integration testing."""
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.storage import get_storage_client
from app.logging import init_logging

logger = init_logging()

def main():
    """Upload a test file to storage."""
    # Create test content
    test_content = b"""This is a test document for the RAG pipeline.
    
    It contains multiple paragraphs to test chunking.
    
    This is the second paragraph with some more content.
    It should be processed by the ingest pipeline.
    
    Final paragraph with conclusion text.
    """
    
    # Upload to storage
    blob_path = "test-tenant/test-dataset/test-document.txt"
    
    print(f"Uploading test file to: {blob_path}")
    
    try:
        storage_client = get_storage_client()
        
        # Upload with metadata
        metadata = {
            "original_name": "test-document.txt",
            "upload_source": "test_script"
        }
        
        success = storage_client.upload(blob_path, test_content, metadata=metadata)
        
        if success:
            print(f"✅ Successfully uploaded test file to {blob_path}")
            print(f"   Size: {len(test_content)} bytes")
            print("\nYou can now test the ingest API with:")
            print(f'curl -X POST http://localhost:8000/api/ingest \\')
            print(f'  -H "Content-Type: application/json" \\')
            print(f'  -d \'{{"blob_path": "{blob_path}"}}\'')
        else:
            print("❌ Upload failed")
            return 1
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())