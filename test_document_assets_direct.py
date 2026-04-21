"""
Direct test of document upload functionality without HTTP server.
Tests the core document_assets module directly.
"""
from pathlib import Path
import sys
import tempfile
import shutil

# Add services to path
sys.path.insert(0, str(Path(__file__).parent))

from services.workspace.document_assets import (
    upload_document_asset,
    list_document_assets,
    DOCUMENT_TYPES,
)

def test_document_types():
    """Test document types are defined correctly."""
    print("\n" + "="*60)
    print("TEST 1: Document Types")
    print("="*60)

    print(f"Available document types: {len(DOCUMENT_TYPES)}")
    for doc_type, info in DOCUMENT_TYPES.items():
        print(f"  - {info['label']} ({doc_type}): Priority {info['priority']}")

    assert len(DOCUMENT_TYPES) == 3, "Should have 3 document types"
    assert "spec" in DOCUMENT_TYPES, "Should have 'spec' type"
    assert "policy" in DOCUMENT_TYPES, "Should have 'policy' type"
    assert "other" in DOCUMENT_TYPES, "Should have 'other' type"

    print("[PASS] Document types are correctly defined")
    return True


def test_upload_document():
    """Test uploading a document to a temporary workspace."""
    print("\n" + "="*60)
    print("TEST 2: Upload Document")
    print("="*60)

    # Create temporary workspace
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_dir = Path(temp_dir) / "test-workspace"
        workspace_dir.mkdir()

        # Create minimal workspace config
        config_file = workspace_dir / "workspace.yaml"
        config_file.write_text("version: 1\n")

        # Test PDF
        test_pdf = Path("documents/fms-08-09-2023-ssds-201-1-ozturk-final.pdf")

        if not test_pdf.exists():
            print(f"[SKIP] Test PDF not found: {test_pdf}")
            return True

        print(f"Uploading: {test_pdf.name}")
        print(f"Size: {test_pdf.stat().st_size / 1024:.1f} KB")

        try:
            # Upload document
            metadata = upload_document_asset(
                workspace_dir=workspace_dir,
                file_path=test_pdf,
                document_type="other",
                display_name="Test FMS Paper",
            )

            print(f"\n[OK] Upload successful!")
            print(f"  Document ID: {metadata['document_id']}")
            print(f"  Display Name: {metadata['display_name']}")
            print(f"  Type: {metadata['document_type']}")
            print(f"  Priority: {metadata['priority']}")
            print(f"  Version: {metadata['version']}")

            # Verify files were created
            doc_assets_dir = workspace_dir / "document-assets"
            assert doc_assets_dir.exists(), "document-assets directory should exist"

            registry_file = doc_assets_dir / "registry.json"
            assert registry_file.exists(), "registry.json should exist"

            print(f"\n[OK] Files created:")
            print(f"  Registry: {registry_file}")
            print(f"  Asset dir: {doc_assets_dir}")

            # Test listing documents
            documents = list_document_assets(workspace_dir)
            assert len(documents) == 1, "Should have 1 document"

            doc = documents[0]
            print(f"\n[OK] Document listed:")
            print(f"  ID: {doc['doc_id']}")
            print(f"  Type: {doc['document_type']}")
            print(f"  Size: {doc['file_size'] / 1024:.1f} KB")

            print("\n[PASS] Upload and list test passed")
            return True

        except Exception as e:
            print(f"\n[FAIL] Upload failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_document_type_filtering():
    """Test filtering documents by type."""
    print("\n" + "="*60)
    print("TEST 3: Document Type Filtering")
    print("="*60)

    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_dir = Path(temp_dir) / "test-workspace"
        workspace_dir.mkdir()

        config_file = workspace_dir / "workspace.yaml"
        config_file.write_text("version: 1\n")

        test_pdf = Path("documents/fms-08-09-2023-ssds-201-1-ozturk-final.pdf")

        if not test_pdf.exists():
            print(f"[SKIP] Test PDF not found")
            return True

        try:
            # Upload documents with different types
            for doc_type in ["spec", "policy", "other"]:
                upload_document_asset(
                    workspace_dir=workspace_dir,
                    file_path=test_pdf,
                    document_type=doc_type,
                    display_name=f"Test {doc_type.title()} Document",
                )

            # List all documents
            all_docs = list_document_assets(workspace_dir)
            print(f"Total documents: {len(all_docs)}")
            assert len(all_docs) == 3, "Should have 3 documents"

            # Filter by type
            for doc_type in ["spec", "policy", "other"]:
                filtered = list_document_assets(workspace_dir, document_type=doc_type)
                print(f"  {doc_type}: {len(filtered)} document(s)")
                assert len(filtered) == 1, f"Should have 1 {doc_type} document"

            print("\n[PASS] Filtering test passed")
            return True

        except Exception as e:
            print(f"\n[FAIL] Filtering test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("DOCUMENT ASSETS MODULE TEST SUITE")
    print("="*60)

    results = []

    # Test 1: Document types
    results.append(("Document Types", test_document_types()))

    # Test 2: Upload document
    results.append(("Upload Document", test_upload_document()))

    # Test 3: Type filtering
    results.append(("Type Filtering", test_document_type_filtering()))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

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
