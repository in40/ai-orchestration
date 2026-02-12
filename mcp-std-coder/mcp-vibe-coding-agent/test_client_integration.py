"""
Integration tests for the MCP server with client methods
Tests the complete flow of server-initiated requests to clients
"""
import asyncio
import threading
import time
import json
from unittest.mock import AsyncMock, patch
from mcp_std_server.server import McpServer
from mcp_std_server.utils.json_rpc import JsonRpcMessage, MessageType
from mcp_std_server.handlers.client_handlers import ClientMethodsHandlers


def test_integration_sampling_complete():
    """Test end-to-end sampling/complete flow"""
    print("Testing sampling/complete integration...")
    
    # Create a server instance
    server = McpServer(transport_type="stdio")
    
    async def run_test():
        # Mock the send_request_to_client method to simulate a successful response
        expected_response = {
            "choices": [
                {
                    "text": "This is a simulated completion response.",
                    "index": 0,
                    "finish_reason": "length"
                }
            ],
            "model": "gpt-4",
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            }
        }
        
        with patch.object(server.rpc_handler, 'send_request_to_client', 
                         return_value=expected_response) as mock_send:
            params = {
                "prompt": "Write a short poem about programming",
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 50
            }
            
            result = await server.client_handlers.request_sampling_complete(params)
            
            # Verify the method was called with correct parameters
            mock_send.assert_called_once_with(
                method="sampling/complete",
                params=params,
                timeout=30.0
            )
            
            # Verify the result structure
            assert "choices" in result
            assert "model" in result
            assert "usage" in result
            print("✅ sampling/complete integration test passed")
            return result
    
    # Run the async test
    result = asyncio.run(run_test())
    return result


def test_integration_elicitation_request():
    """Test end-to-end elicitation/request flow"""
    print("Testing elicitation/request integration...")
    
    # Create a server instance
    server = McpServer(transport_type="stdio")
    
    async def run_test():
        # Mock the send_request_to_client method to simulate a successful response
        expected_response = {
            "input": "yes",
            "type": "confirmation"
        }
        
        with patch.object(server.rpc_handler, 'send_request_to_client', 
                         return_value=expected_response) as mock_send:
            params = {
                "prompt": "Please confirm this action",
                "type": "confirmation",
                "options": ["yes", "no"]
            }
            
            result = await server.client_handlers.request_elicitation(params)
            
            # Verify the method was called with correct parameters
            mock_send.assert_called_once_with(
                method="elicitation/request",
                params=params,
                timeout=30.0
            )
            
            # Verify the result structure
            assert "input" in result
            assert "type" in result
            print("✅ elicitation/request integration test passed")
            return result
    
    # Run the async test
    result = asyncio.run(run_test())
    return result


def test_integration_logging_message():
    """Test end-to-end logging/message flow"""
    print("Testing logging/message integration...")
    
    # Create a server instance
    server = McpServer(transport_type="stdio")
    
    async def run_test():
        # Mock the send_request_to_client method to simulate a successful response
        expected_response = {"status": "logged"}
        
        with patch.object(server.rpc_handler, 'send_request_to_client', 
                         return_value=expected_response) as mock_send:
            params = {
                "level": "info",
                "message": "Test log message from server",
                "logger": "integration-test"
            }
            
            result = await server.client_handlers.send_logging_message(params)
            
            # Verify the method was called with correct parameters
            call_args = mock_send.call_args
            assert call_args[1]['method'] == "logging/message"
            assert call_args[1]['params']['level'] == "info"
            assert call_args[1]['params']['message'] == "Test log message from server"
            assert 'timestamp' in call_args[1]['params']  # Timestamp should be added
            
            # For logging, the result should be the same as what the client returned
            assert result == expected_response
            print("✅ logging/message integration test passed")
            return result
    
    # Run the async test
    result = asyncio.run(run_test())
    return result


def test_error_handling_integration():
    """Test error handling in the integration"""
    print("Testing error handling integration...")
    
    # Create a server instance
    server = McpServer(transport_type="stdio")
    
    async def run_test():
        # Test timeout scenario by using a very short timeout
        params = {
            "prompt": "This will timeout",
            "model": "gpt-4"
        }
        
        # Test timeout error
        with patch.object(server.rpc_handler, 'send_request_to_client', 
                         side_effect=asyncio.TimeoutError("Simulated timeout")):
            result = await server.client_handlers.request_sampling_complete(params)
            
            # Should return an error response, not raise an exception
            assert "error" in result
            assert result["error"]["type"] == "timeout_error"
            print("  ✅ Timeout error handling test passed")
        
        # Test general error
        with patch.object(server.rpc_handler, 'send_request_to_client', 
                         side_effect=Exception("Simulated network error")):
            result = await server.client_handlers.request_elicitation(params)
            
            # Should return an error response, not raise an exception
            assert "error" in result
            assert result["error"]["type"] == "client_error"
            print("  ✅ General error handling test passed")
        
        # Test logging error (should not raise exception, just return empty dict)
        with patch.object(server.rpc_handler, 'send_request_to_client', 
                         side_effect=Exception("Simulated network error")):
            result = await server.client_handlers.send_logging_message(params)
            
            # For logging, should return empty dict even on error
            assert result == {}
            print("  ✅ Logging error handling test passed")
        
        print("✅ Error handling integration test passed")

    # Run the async test
    asyncio.run(run_test())


def test_server_client_interaction():
    """Test the complete server-client interaction cycle"""
    print("Testing complete server-client interaction...")
    
    # Create a server instance
    server = McpServer(transport_type="stdio")
    
    async def run_full_test():
        # Test all three client methods in sequence with mocked responses
        
        # 1. Test sampling/complete
        with patch.object(server.rpc_handler, 'send_request_to_client', 
                         return_value={
                             "choices": [{"text": "sample completion"}],
                             "model": "test-model",
                             "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15}
                         }):
            sampling_params = {
                "prompt": "What is the meaning of life?",
                "model": "mock-model",
                "temperature": 0.5
            }
            sampling_result = await server.client_handlers.request_sampling_complete(sampling_params)
            assert "choices" in sampling_result
            print("  ✅ Sampling/complete successful")
        
        # 2. Test elicitation/request
        with patch.object(server.rpc_handler, 'send_request_to_client', 
                         return_value={"input": "confirmed", "type": "confirmation"}):
            elicitation_params = {
                "prompt": "Do you agree with this statement?",
                "type": "confirmation"
            }
            elicitation_result = await server.client_handlers.request_elicitation(elicitation_params)
            assert "input" in elicitation_result
            print("  ✅ Elicitation/request successful")
        
        # 3. Test logging/message
        with patch.object(server.rpc_handler, 'send_request_to_client', 
                         return_value={"status": "logged"}):
            logging_params = {
                "level": "debug",
                "message": "All client methods tested successfully"
            }
            logging_result = await server.client_handlers.send_logging_message(logging_params)
            assert logging_result == {"status": "logged"}
            print("  ✅ Logging/message successful")
        
        print("✅ Complete server-client interaction test passed")
    
    # Run the async test
    asyncio.run(run_full_test())


def test_bidirectional_communication_infrastructure():
    """Test the bidirectional communication infrastructure"""
    print("Testing bidirectional communication infrastructure...")
    
    # Create a server instance
    server = McpServer(transport_type="stdio")
    
    # Test that the RPC handler has the transport layer set
    assert server.rpc_handler.transport_layer is not None
    print("  ✅ Transport layer properly connected to RPC handler")
    
    # Test that client handlers are connected to server handlers
    assert server.server_handlers.client_handlers is server.client_handlers
    print("  ✅ Client handlers properly connected to server handlers")
    
    # Test that the message callback can handle client responses
    # Create a mock response message
    response_msg = JsonRpcMessage(
        message_type=MessageType.RESPONSE,
        id="test-request-id",
        result={"test": "response"}
    )
    
    # Add a pending request to simulate an active request using asyncio.run
    async def setup_and_test_response():
        import asyncio
        future = asyncio.Future()
        server.rpc_handler.pending_client_requests["test-request-id"] = future
        
        # Handle the response
        server._message_callback(response_msg)
        
        # Verify the future was completed
        assert future.done()
        assert future.result() == {"test": "response"}
    
    asyncio.run(setup_and_test_response())
    print("  ✅ Client response handling works correctly")
    
    print("✅ Bidirectional communication infrastructure test passed")


if __name__ == "__main__":
    print("Running integration tests for MCP server client methods...\n")
    
    try:
        test_integration_sampling_complete()
        test_integration_elicitation_request()
        test_integration_logging_message()
        test_error_handling_integration()
        test_server_client_interaction()
        test_bidirectional_communication_infrastructure()
        
        print("\n🎉 All integration tests passed! The MCP server client methods are working correctly.")
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()