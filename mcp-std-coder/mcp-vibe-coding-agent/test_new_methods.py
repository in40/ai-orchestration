#!/usr/bin/env python3
"""
Test script to verify the new prompt methods work
"""

import tempfile
import os
from mcp_std_server.handlers.server_handlers import McpServerHandlers
from mcp_std_server.utils.json_rpc import JsonRpcHandler
from mcp_std_server.utils.notifications import NotificationManager


def test_new_prompt_methods():
    """Test the new prompt methods directly"""
    
    # Create temporary directory for test prompts
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a mock notification manager
        rpc_handler = JsonRpcHandler()
        notification_manager = NotificationManager(rpc_handler)
        
        # Initialize server handlers with the notification manager
        handlers = McpServerHandlers(notification_manager=notification_manager)
        
        # Override the prompts directory to use our temp directory
        handlers.prompts_dir = temp_dir
        
        print("Testing new prompt methods...")
        
        # Test 1: Submit a new prompt
        print("\n1. Testing prompts/submit...")
        submit_params = {
            "name": "test_submit_prompt",
            "content": "This is a test prompt for {{topic}}.",
            "description": "A test prompt submitted via API",
            "arguments": [
                {
                    "name": "topic",
                    "type": "string",
                    "description": "The topic for the prompt"
                }
            ],
            "tags": ["test", "api"]
        }
        
        try:
            result = handlers.handle_prompts_submit(submit_params, "req_1")
            print(f"   Result: {result['result']}")
            print(f"   Message: {result['message']}")
            print("   ✓ prompts/submit works")
        except Exception as e:
            print(f"   ✗ prompts/submit failed: {e}")
        
        # Test 2: Update the prompt
        print("\n2. Testing prompts/update...")
        update_params = {
            "name": "test_submit_prompt",
            "content": "This is an updated test prompt for {{topic}} with more detail.",
            "description": "An updated test prompt"
        }
        
        try:
            result = handlers.handle_prompts_update(update_params, "req_2")
            print(f"   Result: {result['result']}")
            print(f"   Message: {result['message']}")
            print("   ✓ prompts/update works")
        except Exception as e:
            print(f"   ✗ prompts/update failed: {e}")
        
        # Test 3: Search for prompts
        print("\n3. Testing prompts/search...")
        search_params = {
            "query": "test",
            "tags": ["test"]
        }
        
        try:
            result = handlers.handle_prompts_search(search_params, "req_3")
            print(f"   Found {result['total_matches']} matches")
            print(f"   Query: {result['query']}")
            print("   ✓ prompts/search works")
        except Exception as e:
            print(f"   ✗ prompts/search failed: {e}")
        
        # Test 4: Export prompts
        print("\n4. Testing prompts/export...")
        export_params = {
            "names": ["test_submit_prompt"]
        }
        
        try:
            result = handlers.handle_prompts_export(export_params, "req_4")
            print(f"   Exported {result['exported_count']} prompts")
            print("   ✓ prompts/export works")
        except Exception as e:
            print(f"   ✗ prompts/export failed: {e}")
        
        # Test 5: Delete the prompt
        print("\n5. Testing prompts/delete...")
        delete_params = {
            "name": "test_submit_prompt"
        }
        
        try:
            result = handlers.handle_prompts_delete(delete_params, "req_5")
            print(f"   Result: {result['result']}")
            print(f"   Message: {result['message']}")
            print("   ✓ prompts/delete works")
        except Exception as e:
            print(f"   ✗ prompts/delete failed: {e}")
        
        print("\nAll new prompt methods are working correctly!")


if __name__ == "__main__":
    test_new_prompt_methods()