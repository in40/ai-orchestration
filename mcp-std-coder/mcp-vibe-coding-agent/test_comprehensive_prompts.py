#!/usr/bin/env python3
"""
Comprehensive test for the enhanced prompts functionality
"""

import json
import tempfile
import os
from mcp_std_server.handlers.server_handlers import McpServerHandlers
from mcp_std_server.utils.json_rpc import JsonRpcHandler
from mcp_std_server.utils.notifications import NotificationManager


def test_comprehensive_prompts_functionality():
    """Comprehensive test of the enhanced prompts functionality"""
    
    # Create temporary directory for test prompts
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a mock notification manager
        rpc_handler = JsonRpcHandler()
        notification_manager = NotificationManager(rpc_handler)
        
        # Initialize server handlers with the notification manager
        handlers = McpServerHandlers(notification_manager=notification_manager)
        
        # Override the prompts directory to use our temp directory
        handlers.prompts_dir = temp_dir
        
        print("Running comprehensive tests for prompts functionality...")
        
        # Test 1: Submit a new prompt with all fields
        print("\n1. Testing prompts/submit with all fields...")
        submit_params = {
            "name": "comprehensive_test_prompt",
            "content": "This is a comprehensive test prompt with {{variable1}} and {{variable2}}.",
            "description": "A comprehensive test prompt for demonstration",
            "arguments": [
                {
                    "name": "variable1",
                    "type": "string",
                    "description": "First variable to substitute in the prompt"
                },
                {
                    "name": "variable2",
                    "type": "string",
                    "description": "Second variable to substitute in the prompt"
                }
            ],
            "tags": ["comprehensive", "test", "demo"]
        }
        
        result = handlers.handle_prompts_submit(submit_params, "test_req_1")
        assert result['result'] == 'success', f"Expected success, got {result['result']}"
        assert 'comprehensive_test_prompt' in result['prompt']['name'], "Prompt name not in result"
        print("✅ Submit test passed")
        
        # Test 2: Submit duplicate prompt (should update)
        print("\n2. Testing duplicate prompt submission (should update)...")
        duplicate_params = {
            "name": "comprehensive_test_prompt",
            "content": "This is an updated comprehensive test prompt with {{variable1}} and {{variable2}}.",
            "description": "An updated comprehensive test prompt",
            "tags": ["updated", "comprehensive", "test"]
        }
        
        result = handlers.handle_prompts_submit(duplicate_params, "test_req_2")
        assert result['result'] == 'success', f"Expected success, got {result['result']}"
        assert 'updated' in result['message'], f"Expected update message, got {result['message']}"
        print("✅ Duplicate submission test passed")
        
        # Test 3: Get the updated prompt
        print("\n3. Testing prompts/get with arguments...")
        get_params = {
            "name": "comprehensive_test_prompt",
            "arguments": {
                "variable1": "replaced_value1",
                "variable2": "replaced_value2"
            }
        }
        get_result = handlers.handle_prompts_get(get_params, "test_req_3")
        expected_content = "This is an updated comprehensive test prompt with replaced_value1 and replaced_value2."
        actual_content = get_result['contents'][0]['text']
        assert actual_content == expected_content, f"Expected '{expected_content}', got '{actual_content}'"
        print("✅ Get with arguments test passed")
        
        # Test 4: Update the prompt
        print("\n4. Testing prompts/update...")
        update_params = {
            "name": "comprehensive_test_prompt",
            "content": "Updated comprehensive test prompt with {{variable1}}, {{variable2}}, and {{variable3}}.",
            "description": "An updated comprehensive test prompt with more variables",
            "arguments": [
                {
                    "name": "variable1",
                    "type": "string",
                    "description": "First variable to substitute in the prompt"
                },
                {
                    "name": "variable2",
                    "type": "string",
                    "description": "Second variable to substitute in the prompt"
                },
                {
                    "name": "variable3",
                    "type": "string",
                    "description": "Third variable to substitute in the prompt"
                }
            ]
        }
        update_result = handlers.handle_prompts_update(update_params, "test_req_4")
        assert update_result['result'] == 'success', f"Expected success, got {update_result['result']}"
        assert 'comprehensive_test_prompt' in update_result['message'], "Prompt name not in update message"
        print("✅ Update test passed")
        
        # Test 5: Search for prompts by query
        print("\n5. Testing prompts/search by query...")
        search_params = {
            "query": "comprehensive",
            "tags": ["updated"]
        }
        search_result = handlers.handle_prompts_search(search_params, "test_req_5")
        assert search_result['total_matches'] >= 1, f"Expected at least 1 match, got {search_result['total_matches']}"
        found_prompt = False
        for prompt in search_result['prompts']:
            if prompt['name'] == 'comprehensive_test_prompt':
                found_prompt = True
                break
        assert found_prompt, "Could not find the comprehensive_test_prompt in search results"
        print("✅ Search by query test passed")
        
        # Test 6: Search for prompts by tags only
        print("\n6. Testing prompts/search by tags only...")
        search_params_tags = {
            "tags": ["demo"]  # This should not find our updated prompt since we changed tags
        }
        search_result_tags = handlers.handle_prompts_search(search_params_tags, "test_req_6")
        assert search_result_tags['total_matches'] == 0, f"Expected 0 matches for old tag, got {search_result_tags['total_matches']}"
        print("✅ Search by tags test passed")
        
        # Test 7: Search for prompts by query only (no tags)
        print("\n7. Testing prompts/search by query only...")
        search_params_query_only = {
            "query": "updated"
        }
        search_result_query_only = handlers.handle_prompts_search(search_params_query_only, "test_req_7")
        assert search_result_query_only['total_matches'] >= 1, f"Expected at least 1 match, got {search_result_query_only['total_matches']}"
        print("✅ Search by query only test passed")
        
        # Test 8: Export specific prompts
        print("\n8. Testing prompts/export for specific prompts...")
        export_params = {
            "names": ["comprehensive_test_prompt"]
        }
        export_result = handlers.handle_prompts_export(export_params, "test_req_8")
        assert export_result['exported_count'] == 1, f"Expected 1 exported prompt, got {export_result['exported_count']}"
        assert export_result['prompts'][0]['name'] == 'comprehensive_test_prompt', "Wrong prompt exported"
        print("✅ Export specific prompts test passed")
        
        # Test 9: Export all prompts
        print("\n9. Testing prompts/export for all prompts...")
        export_all_params = {
            "all": True
        }
        export_all_result = handlers.handle_prompts_export(export_all_params, "test_req_9")
        assert export_all_result['exported_count'] >= 1, f"Expected at least 1 exported prompt, got {export_all_result['exported_count']}"
        has_comprehensive = any(p['name'] == 'comprehensive_test_prompt' for p in export_all_result['prompts'])
        assert has_comprehensive, "comprehensive_test_prompt not found in all exports"
        print("✅ Export all prompts test passed")
        
        # Test 10: Error case - submit without name
        print("\n10. Testing error case: submit without name...")
        try:
            bad_submit_params = {
                "content": "This should fail",
                "description": "A prompt without a name"
            }
            handlers.handle_prompts_submit(bad_submit_params, "test_req_10")
            assert False, "Expected ValueError for missing name"
        except ValueError as e:
            assert "Prompt name is required" in str(e), f"Unexpected error message: {e}"
            print("✅ Error case (missing name) test passed")
        
        # Test 11: Error case - get non-existent prompt
        print("\n11. Testing error case: get non-existent prompt...")
        try:
            bad_get_params = {
                "name": "non_existent_prompt",
                "arguments": {}
            }
            handlers.handle_prompts_get(bad_get_params, "test_req_11")
            assert False, "Expected ValueError for non-existent prompt"
        except ValueError as e:
            assert "not found" in str(e), f"Unexpected error message: {e}"
            print("✅ Error case (non-existent prompt) test passed")
        
        # Test 12: Error case - update non-existent prompt
        print("\n12. Testing error case: update non-existent prompt...")
        try:
            bad_update_params = {
                "name": "non_existent_prompt",
                "content": "This should fail"
            }
            handlers.handle_prompts_update(bad_update_params, "test_req_12")
            assert False, "Expected ValueError for non-existent prompt"
        except ValueError as e:
            assert "not found for update" in str(e), f"Unexpected error message: {e}"
            print("✅ Error case (non-existent prompt for update) test passed")
        
        # Test 13: Error case - delete non-existent prompt
        print("\n13. Testing error case: delete non-existent prompt...")
        try:
            bad_delete_params = {
                "name": "non_existent_prompt"
            }
            handlers.handle_prompts_delete(bad_delete_params, "test_req_13")
            assert False, "Expected ValueError for non-existent prompt"
        except ValueError as e:
            assert "not found for deletion" in str(e), f"Unexpected error message: {e}"
            print("✅ Error case (non-existent prompt for deletion) test passed")
        
        # Test 14: Error case - search without query or tags
        print("\n14. Testing error case: search without query or tags...")
        try:
            bad_search_params = {}
            handlers.handle_prompts_search(bad_search_params, "test_req_14")
            assert False, "Expected ValueError for missing search criteria"
        except ValueError as e:
            assert "Either query or tags must be provided" in str(e), f"Unexpected error message: {e}"
            print("✅ Error case (missing search criteria) test passed")
        
        # Test 15: Error case - export without names or all
        print("\n15. Testing error case: export without names or all...")
        try:
            bad_export_params = {}
            handlers.handle_prompts_export(bad_export_params, "test_req_15")
            assert False, "Expected ValueError for missing export criteria"
        except ValueError as e:
            assert "Either 'names' or 'all' parameter must be provided" in str(e), f"Unexpected error message: {e}"
            print("✅ Error case (missing export criteria) test passed")
        
        # Test 16: Delete the prompt
        print("\n16. Testing prompts/delete...")
        delete_params = {
            "name": "comprehensive_test_prompt"
        }
        delete_result = handlers.handle_prompts_delete(delete_params, "test_req_16")
        assert delete_result['result'] == 'success', f"Expected success, got {delete_result['result']}"
        assert 'comprehensive_test_prompt' in delete_result['message'], "Prompt name not in delete message"
        print("✅ Delete test passed")
        
        # Test 17: Verify deletion worked
        print("\n17. Testing that prompt was actually deleted...")
        try:
            get_after_delete_params = {
                "name": "comprehensive_test_prompt",
                "arguments": {}
            }
            handlers.handle_prompts_get(get_after_delete_params, "test_req_17")
            assert False, "Expected ValueError for deleted prompt"
        except ValueError as e:
            assert "not found" in str(e), f"Unexpected error message: {e}"
            print("✅ Verification of deletion test passed")
        
        print("\n🎉 All comprehensive tests passed!")


if __name__ == "__main__":
    test_comprehensive_prompts_functionality()