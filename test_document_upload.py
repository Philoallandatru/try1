"""
Test script for document upload API.

This script tests the document upload functionality by:
1. Uploading a PDF from the documents folder
2. Verifying the upload was successful
3. Listing uploaded documents
4. Checking if the document appears in the retrieval index
"""
import requests
import sys
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:8000"
TOKEN = "change-me"
WORKSPACE = "demo"

# Test PDF file
TEST_PDF = "documents/fms-08-09-2023-ssds-201-1-ozturk-final.pdf"

def test_upload_document():
    """Test uploading a document."""
    print(f"\n{'='*60}")
    print("TEST 1: Upload Document")
    print(f"{'='*60}")

    pdf_path = Path(TEST_PDF)
    if not pdf_path.exists():
        print(f"[FAIL] Test PDF not found: {TEST_PDF}")
        return False

    print(f"[*] Uploading: {pdf_path.name}")
    print(f"    Size: {pdf_path.stat().st_size / 1024:.1f} KB")

    url = f"{BASE_URL}/api/documents/upload"
    headers = {"Authorization": f"Bearer {TOKEN}"}

    with open(pdf_path, "rb") as f:
        files = {"file": (pdf_path.name, f, "application/pdf")}
        data = {
            "workspace": WORKSPACE,
            "document_type": "other",
            "display_name": "FMS 2023 SSD Paper"
        }

        try:
            response = requests.post(url, headers=headers, files=files, data=data, timeout=300)

            if response.status_code == 200:
                result = response.json()
                print(f"[OK] Upload successful!")
                print(f"     Document ID: {result['metadata']['document_id']}")
                print(f"     Display Name: {result['metadata']['display_name']}")
                print(f"     Type: {result['metadata']['document_type']}")
                print(f"     Version: {result['metadata']['version']}")
                return True
            else:
                print(f"[FAIL] Upload failed: {response.status_code}")
                print(f"       Response: {response.text}")
                return False
        except Exception as e:
            print(f"[ERROR] {e}")
            return False


def test_list_documents():
    """Test listing uploaded documents."""
    print(f"\n{'='*60}")
    print("TEST 2: List Documents")
    print(f"{'='*60}")

    url = f"{BASE_URL}/api/documents/list"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    params = {"workspace": WORKSPACE}

    try:
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            result = response.json()
            count = result.get("count", 0)
            print(f"[OK] Found {count} document(s)")

            for doc in result.get("documents", []):
                print(f"\n    [DOC] {doc['display_name']}")
                print(f"          ID: {doc['doc_id']}")
                print(f"          Type: {doc['document_type']}")
                print(f"          Size: {doc['file_size'] / 1024:.1f} KB")
                print(f"          Uploaded: {doc['created_at']}")

            return True
        else:
            print(f"[FAIL] List failed: {response.status_code}")
            print(f"       Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_document_types():
    """Test getting document types."""
    print(f"\n{'='*60}")
    print("TEST 3: Get Document Types")
    print(f"{'='*60}")

    url = f"{BASE_URL}/api/documents/types"
    headers = {"Authorization": f"Bearer {TOKEN}"}

    try:
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            result = response.json()
            types = result.get("types", {})
            print(f"[OK] Found {len(types)} document type(s)")

            for type_key, type_info in types.items():
                print(f"\n    [TYPE] {type_info['label']} ({type_key})")
                print(f"           Priority: {type_info['priority']}")

            return True
        else:
            print(f"[FAIL] Get types failed: {response.status_code}")
            print(f"       Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_retrieval_stats():
    """Test retrieval index stats to see if document is indexed."""
    print(f"\n{'='*60}")
    print("TEST 4: Check Retrieval Index")
    print(f"{'='*60}")

    url = f"{BASE_URL}/api/retrieval/stats"
    headers = {"Authorization": f"Bearer {TOKEN}"}
    params = {"workspace_dir": f"workspaces/{WORKSPACE}"}

    try:
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            result = response.json()
            stats = result.get("stats", {})
            total_docs = stats.get("total_documents", 0)
            print(f"[OK] Index contains {total_docs} document(s)")

            if stats.get("last_updated"):
                print(f"     Last updated: {stats['last_updated']}")

            return True
        else:
            print(f"[FAIL] Stats failed: {response.status_code}")
            print(f"       Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("DOCUMENT UPLOAD API TEST SUITE")
    print("="*60)
    print(f"Base URL: {BASE_URL}")
    print(f"Workspace: {WORKSPACE}")
    print(f"Test PDF: {TEST_PDF}")

    results = []

    # Test 1: Upload document
    results.append(("Upload Document", test_upload_document()))

    # Test 2: List documents
    results.append(("List Documents", test_list_documents()))

    # Test 3: Get document types
    results.append(("Get Document Types", test_document_types()))

    # Test 4: Check retrieval index
    results.append(("Check Retrieval Index", test_retrieval_stats()))

    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} - {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n[SUCCESS] All tests passed!")
        return 0
    else:
        print(f"\n[WARNING] {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
