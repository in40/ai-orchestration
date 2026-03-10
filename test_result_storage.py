#!/usr/bin/env python3
"""
Test script for MCP Result Storage System
Tests Git storage, file storage, and result router functionality
"""
import os
import sys
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_git_storage():
    """Test Git storage module"""
    print("=" * 60)
    print("Testing Git Storage Module")
    print("=" * 60)
    
    try:
        from it_lead_mcp_server.utils.git_result_storage import get_git_storage
        
        # Initialize storage with remote Git repository
        storage = get_git_storage(
            repo_path="ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git"
        )
        
        print(f"✅ Git storage initialized")
        print(f"   Local clone: {storage._local_clone_path}")
        print(f"   Remote URL: {storage.repo_path}")
        
        # Test storing code
        result = storage.store_code_result(
            task_id="test-git-storage-001",
            code="def hello():\n    print('Hello from Git Storage!')",
            language="python",
            metadata={"test": True}
        )
        
        print(f"✅ Code result stored")
        print(f"   Commit SHA: {result.get('commit_sha')}")
        print(f"   Storage type: {result.get('storage_type')}")
        
        # Test storing document
        doc_result = storage.store_document_result(
            task_id="test-git-doc-001",
            content="# Test Document\n\nThis is a test document stored in Git.",
            document_type="markdown"
        )
        
        print(f"✅ Document result stored")
        print(f"   Commit SHA: {doc_result.get('commit_sha')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Git storage test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_storage():
    """Test file storage module"""
    print("\n" + "=" * 60)
    print("Testing File Storage Module")
    print("=" * 60)
    
    try:
        from it_lead_mcp_server.utils.file_result_storage import get_file_storage
        
        # Initialize local file storage
        storage = get_file_storage(
            base_path="/tmp/mcp-test-files",
            storage_backend="local"
        )
        
        print(f"✅ File storage initialized")
        print(f"   Base path: {storage.base_path}")
        
        # Test storing a file
        result = storage.store_file(
            task_id="test-file-001",
            file_content=b"This is test file content for the MCP Result Storage System.",
            filename="test.txt",
            content_type="text/plain"
        )
        
        print(f"✅ File stored")
        print(f"   Storage type: {result.get('storage_type')}")
        print(f"   File path: {result.get('file_path')}")
        print(f"   Checksum: {result.get('checksum')}")
        
        return True
        
    except Exception as e:
        print(f"❌ File storage test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_result_router():
    """Test result router module"""
    print("\n" + "=" * 60)
    print("Testing Result Router")
    print("=" * 60)
    
    try:
        from it_lead_mcp_server.utils.result_router import get_result_router
        
        # Initialize router
        router = get_result_router()
        
        print(f"✅ Result router initialized")
        
        # Test routing code result
        code_result = router.route_result(
            task_id="test-router-code-001",
            result_data={
                "code": "def test():\n    return 42",
                "language": "python",
                "explanation": "This is a test function"
            },
            agent="Implementation Engineer",
            tool="vibe_code"
        )
        
        print(f"✅ Code result routed")
        print(f"   Storage type: {code_result.get('storage_type')}")
        print(f"   Commit SHA: {code_result.get('commit_sha')}")
        
        # Test routing document result
        doc_result = router.route_result(
            task_id="test-router-doc-001",
            result_data="# Test Result\n\nThis is a test document.",
            agent="Requirements Engineer",
            tool="analyze_requirements"
        )
        
        print(f"✅ Document result routed")
        print(f"   Storage type: {doc_result.get('storage_type')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Result router test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_task_storage_integration():
    """Test TaskStorage update_task_result_reference method"""
    print("\n" + "=" * 60)
    print("Testing TaskStorage Integration")
    print("=" * 60)
    
    try:
        from it_lead_mcp_server.utils.task_storage import TaskStorage
        
        # Initialize task storage (SQLite)
        storage = TaskStorage(use_sqlite=True, database="mcp_registry.db")
        
        print(f"✅ TaskStorage initialized")
        
        # Create a test task
        test_task_id = "test-integration-001"
        storage.store_received_task(
            task_id=test_task_id,
            title="Test Integration Task",
            description="Testing result storage integration",
            status="received"
        )
        
        print(f"✅ Test task created: {test_task_id}")
        
        # Update with result reference
        storage_ref = {
            "storage_type": "git",
            "commit_sha": "test-commit-sha",
            "path": "results/test-integration-001/",
            "code_file": "/tmp/test/result.py"
        }
        
        success = storage.update_task_result_reference(
            task_id=test_task_id,
            storage_ref=storage_ref,
            metadata={"test": True}
        )
        
        if success:
            print(f"✅ Task result reference updated")
            
            # Verify
            task = storage.get_task(test_task_id)
            if task:
                result = task.get("result")
                if result:
                    result_data = json.loads(result) if isinstance(result, str) else result
                    print(f"   Stored reference: {json.dumps(result_data, indent=2)[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ TaskStorage integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("MCP Result Storage System - Test Suite")
    print("=" * 60)
    print()
    
    results = {
        "Git Storage": test_git_storage(),
        "File Storage": test_file_storage(),
        "Result Router": test_result_router(),
        "TaskStorage Integration": test_task_storage_integration()
    }
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
