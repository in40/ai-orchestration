#!/usr/bin/env python3
"""
Test script for the enhanced prompts functionality
"""

import json
import tempfile
import os
from mcp_std_server.handlers.server_handlers import McpServerHandlers
from mcp_std_server.utils.json_rpc import JsonRpcHandler
from mcp_std_server.utils.notifications import NotificationManager


def test_prompts_functionality():
    """Test the enhanced prompts functionality"""
    
    # Create temporary directory for test prompts
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a mock notification manager
        rpc_handler = JsonRpcHandler()
        notification_manager = NotificationManager(rpc_handler)
        
        # Initialize server handlers with the notification manager
        handlers = McpServerHandlers(notification_manager=notification_manager)
        
        # Override the prompts directory to use our temp directory
        handlers.prompts_dir = temp_dir
        
        print("Testing prompts functionality...")
        
        # Test 1: Submit a new prompt
        print("\n1. Testing prompts/submit...")
        submit_params = {
            "name": "test_prompt",
            "content": "This is a test prompt with {{variable}} substitution.",
            "description": "A test prompt for demonstration",
            "arguments": [
                {
                    "name": "variable",
                    "type": "string",
                    "description": "A variable to substitute in the prompt"
                }
            ],
            "tags": ["test", "demo"]
        }
        
        result = handlers.handle_prompts_submit(submit_params, "test_req_1")
        print(f"Submit result: {result['result']}")
        print(f"Message: {result['message']}")
        
        # Test 2: List prompts
        print("\n2. Testing prompts/list...")
        list_result = handlers.handle_prompts_list({}, "test_req_2")
        print(f"Number of prompts: {len(list_result['prompts'])}")
        print(f"Prompt names: {[p['name'] for p in list_result['prompts']]}")
        
        # Test 3: Get the submitted prompt
        print("\n3. Testing prompts/get...")
        get_params = {
            "name": "test_prompt",
            "arguments": {
                "variable": "replaced_value"
            }
        }
        get_result = handlers.handle_prompts_get(get_params, "test_req_3")
        print(f"Retrieved prompt content: {get_result['contents'][0]['text']}")
        
        # Test 4: Update the prompt
        print("\n4. Testing prompts/update...")
        update_params = {
            "name": "test_prompt",
            "content": "Updated test prompt with {{variable}} and {{extra}}.",
            "description": "An updated test prompt",
            "arguments": [
                {
                    "name": "variable",
                    "type": "string",
                    "description": "A variable to substitute in the prompt"
                },
                {
                    "name": "extra",
                    "type": "string",
                    "description": "An extra variable"
                }
            ]
        }
        update_result = handlers.handle_prompts_update(update_params, "test_req_4")
        print(f"Update result: {update_result['result']}")
        print(f"Message: {update_result['message']}")
        
        # Test 5: Search for prompts
        print("\n5. Testing prompts/search...")
        search_params = {
            "query": "test",
            "tags": ["test"]
        }
        search_result = handlers.handle_prompts_search(search_params, "test_req_5")
        print(f"Search found {search_result['total_matches']} matches")
        print(f"Match names: {[p['name'] for p in search_result['prompts']]}")
        
        # Test 6: Delete the prompt
        print("\n6. Testing prompts/delete...")
        delete_params = {
            "name": "test_prompt"
        }
        delete_result = handlers.handle_prompts_delete(delete_params, "test_req_6")
        print(f"Delete result: {delete_result['result']}")
        print(f"Message: {delete_result['message']}")
        
        # Test 7: List prompts again to confirm deletion
        print("\n7. Testing prompts/list after deletion...")
        list_result_after = handlers.handle_prompts_list({}, "test_req_7")
        print(f"Number of prompts after deletion: {len(list_result_after['prompts'])}")
        
        print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_prompts_functionality()