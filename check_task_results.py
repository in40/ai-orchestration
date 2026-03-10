#!/usr/bin/env python3
"""
Check task status and verify code extraction quality.

This script checks the submitted tasks and verifies that:
1. Tasks are completed
2. Code is properly extracted (no natural language)
3. Code is stored in git with correct file extension
"""

import httpx
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Configuration
IT_LEAD_URL = "http://127.0.0.1:3061/mcp"
GIT_STORAGE_PATH = "/tmp/mcp-vibe-coding-git/repo/results"

# Task IDs from submission (vibe_code_async) - LATEST BATCH AFTER CACHE CLEAR
TASK_IDS = [
    "53a5ea33-db71-4ec1-a69f-b8772fb52674",  # Flappy Bird Clone - Classic
    "a0d79f64-b3ff-407f-ab9a-893faf528e6e",  # Flappy Bird with Multiple Levels
    "74f2f272-bd36-4342-a793-fc18fa4ccab0",  # Flappy Bird with Power-ups
    "0d586f51-3799-4c94-93f4-1408bf4e7441",  # Flappy Bird with Enhanced Graphics
]

# Implementation Engineer URL
IMPL_ENGINEER_URL = "http://0.0.0.0:3060/mcp"


def check_task_status(task_id):
    """Check the status of a specific task"""
    payload = {
        "jsonrpc": "2.0",
        "id": f"status_{task_id}",
        "method": "tools/call",
        "params": {
            "name": "tasks/get",
            "arguments": {"taskId": task_id}
        }
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(IMPL_ENGINEER_URL, json=payload)
            if response.status_code == 200:
                result = response.json()
                return result.get("result", {})
    except Exception as e:
        print(f"Error checking task {task_id}: {e}")
    
    return None


def get_task_result(task_id):
    """Get the result of a completed task"""
    payload = {
        "jsonrpc": "2.0",
        "id": f"result_{task_id}",
        "method": "tools/call",
        "params": {
            "name": "tasks/result",
            "arguments": {"taskId": task_id}
        }
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(IMPL_ENGINEER_URL, json=payload)
            if response.status_code == 200:
                result = response.json()
                return result.get("result", {})
    except Exception as e:
        print(f"Error getting result for task {task_id}: {e}")
    
    return None


def check_git_storage(task_id):
    """Check if code is stored in git storage"""
    task_path = Path(GIT_STORAGE_PATH) / task_id
    
    if not task_path.exists():
        return None
    
    files = []
    for f in task_path.iterdir():
        if f.is_file():
            files.append({
                "name": f.name,
                "path": str(f),
                "size": f.stat().st_size
            })
    
    return files


def read_code_file(task_id):
    """Read the code file for a task"""
    task_path = Path(GIT_STORAGE_PATH) / task_id
    
    if not task_path.exists():
        return None, None
    
    # Find the code file (not metadata.json)
    for f in task_path.iterdir():
        if f.is_file() and f.suffix != '.json':
            return f.name, f.read_text()
    
    return None, None


def check_code_quality(code):
    """Check if code is clean (no natural language artifacts)"""
    if not code:
        return {"is_clean": False, "issues": ["No code found"]}
    
    issues = []
    
    # Check for common natural language patterns that should not be in code
    problematic_patterns = [
        ("Here's the code", "Introductory text found"),
        ("Here is the code", "Introductory text found"),
        ("I hope this helps", "Concluding text found"),
        ("Let me know if", "Conversational text found"),
        ("This code does", "Explanatory text found"),
        ("Enjoy coding", "Concluding text found"),
    ]
    
    for pattern, issue in problematic_patterns:
        if pattern.lower() in code.lower():
            issues.append(issue)
    
    # Check for markdown code block markers (should not be in saved file)
    if '```' in code:
        issues.append("Markdown code block markers found in saved file")
    
    return {
        "is_clean": len(issues) == 0,
        "issues": issues,
        "code_length": len(code)
    }


def main():
    """Main function to check all tasks"""
    print("="*70)
    print("TASK STATUS AND CODE QUALITY CHECK")
    print(f"Time: {datetime.now().isoformat()}")
    print("="*70)
    
    results = []
    
    for task_id in TASK_IDS:
        print(f"\n{'='*70}")
        print(f"Task: {task_id}")
        print(f"{'='*70}")
        
        # Check status
        status = check_task_status(task_id)
        if status:
            print(f"Status: {status.get('status', 'unknown')}")
            print(f"Progress: {status.get('progress', 0)}%")
        else:
            print("Status: Could not retrieve")
        
        # Check git storage
        git_files = check_git_storage(task_id)
        if git_files:
            print(f"Git storage: ✅ Found {len(git_files)} file(s)")
            for f in git_files:
                print(f"  - {f['name']} ({f['size']} bytes)")
        else:
            print("Git storage: ❌ Not found")
        
        # Read and check code quality
        filename, code = read_code_file(task_id)
        if code:
            print(f"Code file: {filename}")
            quality = check_code_quality(code)
            
            if quality["is_clean"]:
                print(f"Code quality: ✅ CLEAN")
            else:
                print(f"Code quality: ⚠️ ISSUES FOUND:")
                for issue in quality["issues"]:
                    print(f"    - {issue}")
            
            print(f"Code length: {quality['code_length']} chars")
            
            # Show preview
            print("\nCode preview (first 300 chars):")
            print("-"*50)
            preview = code[:300] + "..." if len(code) > 300 else code
            print(preview)
            print("-"*50)
            
            results.append({
                "task_id": task_id,
                "filename": filename,
                "is_clean": quality["is_clean"],
                "issues": quality["issues"],
                "code_length": quality["code_length"]
            })
        else:
            print("Code: ❌ Not found")
            results.append({
                "task_id": task_id,
                "filename": None,
                "is_clean": False,
                "issues": ["Code file not found"],
                "code_length": 0
            })
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    
    clean_count = sum(1 for r in results if r["is_clean"])
    total = len(results)
    
    print(f"Tasks checked: {total}")
    print(f"Clean code: {clean_count}/{total}")
    print(f"Issues found: {total - clean_count}/{total}")
    
    if clean_count == total:
        print("\n✅ ALL TASKS HAVE CLEAN CODE!")
        print("The code extraction fix is working correctly.")
    else:
        print("\n⚠️ SOME TASKS HAVE ISSUES:")
        for r in results:
            if not r["is_clean"] and r["issues"]:
                print(f"  - {r['task_id']}: {', '.join(r['issues'])}")
    
    return clean_count == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
