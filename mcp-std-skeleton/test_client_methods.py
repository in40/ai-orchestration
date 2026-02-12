"""
Unit tests for client methods handlers in the MCP server
Tests the three standard MCP client methods that the server can initiate:
- sampling/complete
- elicitation/request
- logging/message
"""
import asyncio
import unittest.mock as mock
from mcp_std_server.handlers.client_handlers import ClientMethodsHandlers
from mcp_std_server.utils.json_rpc import JsonRpcHandler, JsonRpcMessage, MessageType
import pytest


class TestClientMethodsHandlers:
    """Test suite for client methods handlers"""

    def setup_method(self):
        """Setup test fixtures before each test method."""
        self.rpc_handler = JsonRpcHandler()
        self.client_handlers = ClientMethodsHandlers(self.rpc_handler)

    @pytest.mark.asyncio
    async def test_request_sampling_complete_success(self):
        """Test successful sampling/complete request"""
        # Mock the RPC handler's send_request_to_client method
        expected_result = {
            "choices": [{"text": "generated text"}],
            "model": "gpt-4",
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        }
        
        with mock.patch.object(self.rpc_handler, 'send_request_to_client', 
                              return_value=expected_result) as mock_send:
            params = {
                "prompt": "Write a story about cats",
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 100
            }
            
            result = await self.client_handlers.request_sampling_complete(params)
            
            # Verify the method was called with correct parameters
            mock_send.assert_called_once_with(
                method="sampling/complete",
                params=params,
                timeout=30.0
            )
            
            assert result == expected_result

    @pytest.mark.asyncio
    async def test_request_sampling_complete_timeout(self):
        """Test sampling/complete request with timeout"""
        with mock.patch.object(self.rpc_handler, 'send_request_to_client', 
                              side_effect=asyncio.TimeoutError()) as mock_send:
            params = {
                "prompt": "Write a story about cats",
                "model": "gpt-4"
            }
            
            result = await self.client_handlers.request_sampling_complete(params)
            
            # Verify the method was called
            mock_send.assert_called_once()
            
            # Check that the error response is properly formatted
            assert "error" in result
            assert result["error"]["type"] == "timeout_error"
            assert "Timeout waiting for sampling/complete response" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_request_sampling_complete_general_error(self):
        """Test sampling/complete request with general error"""
        with mock.patch.object(self.rpc_handler, 'send_request_to_client', 
                              side_effect=Exception("Network error")) as mock_send:
            params = {
                "prompt": "Write a story about cats",
                "model": "gpt-4"
            }
            
            result = await self.client_handlers.request_sampling_complete(params)
            
            # Verify the method was called
            mock_send.assert_called_once()
            
            # Check that the error response is properly formatted
            assert "error" in result
            assert result["error"]["type"] == "client_error"
            assert "Failed to get completion from client" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_request_elicitation_success(self):
        """Test successful elicitation/request"""
        expected_result = {
            "input": "user provided text",
            "type": "text"
        }
        
        with mock.patch.object(self.rpc_handler, 'send_request_to_client', 
                              return_value=expected_result) as mock_send:
            params = {
                "prompt": "Please enter your name",
                "type": "text"
            }
            
            result = await self.client_handlers.request_elicitation(params)
            
            # Verify the method was called with correct parameters
            mock_send.assert_called_once_with(
                method="elicitation/request",
                params=params,
                timeout=30.0
            )
            
            assert result == expected_result

    @pytest.mark.asyncio
    async def test_request_elicitation_timeout(self):
        """Test elicitation/request with timeout"""
        with mock.patch.object(self.rpc_handler, 'send_request_to_client', 
                              side_effect=asyncio.TimeoutError()) as mock_send:
            params = {
                "prompt": "Please enter your name",
                "type": "text"
            }
            
            result = await self.client_handlers.request_elicitation(params)
            
            # Verify the method was called
            mock_send.assert_called_once()
            
            # Check that the error response is properly formatted
            assert "error" in result
            assert result["error"]["type"] == "timeout_error"
            assert "Timeout waiting for elicitation/request response" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_request_elicitation_general_error(self):
        """Test elicitation/request with general error"""
        with mock.patch.object(self.rpc_handler, 'send_request_to_client', 
                              side_effect=Exception("Network error")) as mock_send:
            params = {
                "prompt": "Please enter your name",
                "type": "text"
            }
            
            result = await self.client_handlers.request_elicitation(params)
            
            # Verify the method was called
            mock_send.assert_called_once()
            
            # Check that the error response is properly formatted
            assert "error" in result
            assert result["error"]["type"] == "client_error"
            assert "Failed to get user input from client" in result["error"]["message"]

    @pytest.mark.asyncio
    async def test_send_logging_message_success(self):
        """Test successful logging/message"""
        expected_result = {}
        
        with mock.patch.object(self.rpc_handler, 'send_request_to_client', 
                              return_value=expected_result) as mock_send:
            params = {
                "level": "info",
                "message": "Operation completed successfully"
            }
            
            result = await self.client_handlers.send_logging_message(params)
            
            # Verify the method was called with correct parameters
            # Check that timestamp was added if not present
            called_kwargs = mock_send.call_args[1]
            assert called_kwargs['method'] == "logging/message"
            assert 'timestamp' in called_kwargs['params']
            assert called_kwargs['params']['level'] == "info"
            assert called_kwargs['params']['message'] == "Operation completed successfully"
            
            assert result == expected_result

    @pytest.mark.asyncio
    async def test_send_logging_message_timeout(self):
        """Test logging/message with timeout"""
        with mock.patch.object(self.rpc_handler, 'send_request_to_client', 
                              side_effect=asyncio.TimeoutError()) as mock_send:
            params = {
                "level": "info",
                "message": "Operation completed successfully"
            }
            
            # Capture print output to verify logging
            with mock.patch('builtins.print') as mock_print:
                result = await self.client_handlers.send_logging_message(params)
                
                # Verify the method was called
                mock_send.assert_called_once()
                
                # Check that the result is empty dict (not an error)
                assert result == {}
                
                # Verify that the timeout was logged
                mock_print.assert_called()
                assert any("Timeout sending to client" in str(call) for call in mock_print.call_args_list)

    @pytest.mark.asyncio
    async def test_send_logging_message_general_error(self):
        """Test logging/message with general error"""
        with mock.patch.object(self.rpc_handler, 'send_request_to_client', 
                              side_effect=Exception("Network error")) as mock_send:
            params = {
                "level": "info",
                "message": "Operation completed successfully"
            }
            
            # Capture print output to verify logging
            with mock.patch('builtins.print') as mock_print:
                result = await self.client_handlers.send_logging_message(params)
                
                # Verify the method was called
                mock_send.assert_called_once()
                
                # Check that the result is empty dict (not an error)
                assert result == {}
                
                # Verify that the error was logged
                mock_print.assert_called()
                assert any("Failed to send to client" in str(call) for call in mock_print.call_args_list)

    @pytest.mark.asyncio
    async def test_send_logging_message_preserves_timestamp(self):
        """Test that logging/message preserves existing timestamp"""
        expected_result = {}
        
        with mock.patch.object(self.rpc_handler, 'send_request_to_client', 
                              return_value=expected_result) as mock_send:
            params = {
                "level": "info",
                "message": "Operation completed successfully",
                "timestamp": "2023-01-01T00:00:00Z"
            }
            
            result = await self.client_handlers.send_logging_message(params)
            
            # Verify the method was called with the original timestamp preserved
            called_kwargs = mock_send.call_args[1]
            assert called_kwargs['params']['timestamp'] == "2023-01-01T00:00:00Z"
            assert called_kwargs['params']['level'] == "info"
            assert called_kwargs['params']['message'] == "Operation completed successfully"


class TestJsonRpcHandlerBidirectional:
    """Test the bidirectional communication infrastructure"""

    def setup_method(self):
        """Setup test fixtures before each test method."""
        self.rpc_handler = JsonRpcHandler()
        # Mock transport layer
        self.mock_transport = mock.Mock()
        self.rpc_handler.set_transport_layer(self.mock_transport)

    @pytest.mark.asyncio
    async def test_send_request_to_client_success(self):
        """Test successful sending of request to client"""
        params = {"prompt": "test prompt"}
        
        # Simulate response later
        async def simulate_response():
            await asyncio.sleep(0.01)  # Small delay
            # Create a mock response message
            response_msg = JsonRpcMessage(
                message_type=MessageType.RESPONSE,
                id=None,  # Will be set when we get the actual request ID
                result={"choices": [{"text": "response"}]}
            )
            # We need to get the actual request ID from the call
            call_args = self.mock_transport.send_message.call_args
            if call_args:
                request_msg = call_args[0][0]
                response_msg.id = request_msg.id
                self.rpc_handler.handle_client_response(response_msg)

        # Start the response simulation
        asyncio.create_task(simulate_response())
        
        # Make the actual call
        result = await self.rpc_handler.send_request_to_client(
            method="sampling/complete", 
            params=params
        )
        
        # Verify the request was sent
        assert self.mock_transport.send_message.called
        sent_message = self.mock_transport.send_message.call_args[0][0]
        assert sent_message.method == "sampling/complete"
        assert sent_message.params == params
        assert sent_message.message_type == MessageType.REQUEST
        assert sent_message.id is not None
        
        # Verify the result
        assert result == {"choices": [{"text": "response"}]}

    @pytest.mark.asyncio
    async def test_send_request_to_client_timeout(self):
        """Test timeout when sending request to client"""
        params = {"prompt": "test prompt"}
        
        with pytest.raises(asyncio.TimeoutError):
            await self.rpc_handler.send_request_to_client(
                method="sampling/complete", 
                params=params,
                timeout=0.01  # Very short timeout to force timeout
            )

    def test_handle_client_response_success(self):
        """Test handling of successful client response"""
        # First, create a pending request
        request_future = asyncio.Future()
        request_id = "test-id-123"
        self.rpc_handler.pending_client_requests[request_id] = request_future
        
        # Create a response message
        response_message = JsonRpcMessage(
            message_type=MessageType.RESPONSE,
            id=request_id,
            result={"data": "response_data"}
        )
        
        # Handle the response
        self.rpc_handler.handle_client_response(response_message)
        
        # Verify the future was completed
        assert request_future.done()
        assert request_future.result() == {"data": "response_data"}
        # Verify the request was removed from pending requests
        assert request_id not in self.rpc_handler.pending_client_requests

    def test_handle_client_response_error(self):
        """Test handling of client response with error"""
        # First, create a pending request
        request_future = asyncio.Future()
        request_id = "test-id-123"
        self.rpc_handler.pending_client_requests[request_id] = request_future
        
        # Create an error response message
        error_response = JsonRpcMessage(
            message_type=MessageType.RESPONSE,
            id=request_id,
            error={"code": -32601, "message": "Method not found"}
        )
        
        # Handle the response
        self.rpc_handler.handle_client_response(error_response)
        
        # Verify the future was completed with an exception
        assert request_future.done()
        with pytest.raises(Exception) as exc_info:
            request_future.result()
        assert "Method not found" in str(exc_info.value)
        # Verify the request was removed from pending requests
        assert request_id not in self.rpc_handler.pending_client_requests

    def test_handle_client_response_unknown_request_id(self):
        """Test handling of client response with unknown request ID"""
        # Create a response message with unknown ID
        response_message = JsonRpcMessage(
            message_type=MessageType.RESPONSE,
            id="unknown-id",
            result={"data": "response_data"}
        )
        
        # Handle the response - should not crash
        self.rpc_handler.handle_client_response(response_message)
        
        # Nothing should happen since there's no pending request for this ID


if __name__ == "__main__":
    pytest.main([__file__, "-v"])