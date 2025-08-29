#!/usr/bin/env python3
"""End-to-end test of the ingest pipeline."""
import sys
import time
import json
import requests
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.storage import get_storage_client
from app.logging import init_logging

logger = init_logging()

API_BASE = "http://localhost:8000"

def test_e2e_ingest():
    """Test end-to-end ingest pipeline."""
    print("🧪 RAG Pipeline E2E Test")
    print("="*40)
    
    # Step 1: Upload test file
    print("1. Uploading test file to storage...")
    blob_path = "test-tenant/test-dataset/sample-doc.txt"
    test_content = b"""Sample Document for RAG Testing

This is the first paragraph of our test document.
It contains some information that should be indexed.

Second paragraph with different content.
This will be chunked separately for better retrieval.

Final paragraph with conclusion information.
This completes our sample document."""
    
    try:
        storage_client = get_storage_client()
        storage_client.upload(blob_path, test_content)
        print(f"   ✅ Uploaded {len(test_content)} bytes to {blob_path}")
    except Exception as e:
        print(f"   ❌ Upload failed: {e}")
        return False
    
    # Step 2: Submit ingest job
    print("2. Submitting ingest job...")
    ingest_data = {
        "blob_path": blob_path,
        "tags": {
            "tenant": "test-tenant",
            "dataset": "test-dataset",
            "doc_type": "sample"
        }
    }
    
    try:
        response = requests.post(
            f"{API_BASE}/api/ingest",
            json=ingest_data,
            timeout=10
        )
        response.raise_for_status()
        job_data = response.json()
        job_id = job_data["job_id"]
        print(f"   ✅ Job submitted: {job_id}")
    except Exception as e:
        print(f"   ❌ Ingest submission failed: {e}")
        return False
    
    # Step 3: Monitor job status
    print("3. Monitoring job status...")
    max_attempts = 30
    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{API_BASE}/api/ingest/{job_id}")
            response.raise_for_status()
            status_data = response.json()
            
            status = status_data["status"]
            print(f"   Attempt {attempt + 1}/30: Status = {status}")
            
            if status == "done":
                print(f"   ✅ Job completed successfully!")
                print(f"   📊 Counts: {status_data.get('counts', {})}")
                print(f"   📄 Doc ID: {status_data.get('doc_id')}")
                return True
            elif status == "failed":
                print(f"   ❌ Job failed: {status_data.get('error')}")
                return False
            elif status in ["pending", "processing"]:
                time.sleep(2)  # Wait 2 seconds before checking again
                continue
            else:
                print(f"   ❓ Unknown status: {status}")
                
        except Exception as e:
            print(f"   ❌ Status check failed: {e}")
            return False
    
    print("   ⏰ Job did not complete within timeout")
    return False

def test_api_health():
    """Test that API is responding."""
    print("0. Checking API health...")
    try:
        response = requests.get(f"{API_BASE}/healthz", timeout=5)
        response.raise_for_status()
        print("   ✅ API is healthy")
        return True
    except Exception as e:
        print(f"   ❌ API health check failed: {e}")
        print("   💡 Make sure API is running: docker-compose up -d api")
        return False

def main():
    """Run the E2E test."""
    print("Starting RAG Pipeline E2E Test...")
    
    # Check API health first
    if not test_api_health():
        return 1
    
    # Run E2E test
    if test_e2e_ingest():
        print("\n🎉 E2E Test PASSED!")
        print("\nNext steps:")
        print("- Check logs: docker logs rag_api")
        print("- Check worker logs: docker logs rag_worker")
        print("- Check OpenSearch: curl 'http://localhost:9200/chunks_current/_count'")
        return 0
    else:
        print("\n💥 E2E Test FAILED!")
        print("\nDebugging tips:")
        print("- Check all services: docker-compose ps")
        print("- Check API logs: docker logs rag_api")
        print("- Check worker logs: docker logs rag_worker")
        return 1

if __name__ == "__main__":
    sys.exit(main())