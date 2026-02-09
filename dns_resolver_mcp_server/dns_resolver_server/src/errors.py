"""
Error Handling Module

This module defines error classes and handling mechanisms that comply with JSON-RPC 2.0 standards.
"""

from typing import Any, Optional
from enum import IntEnum


class RPCErrorCode(IntEnum):
    """
    Standard JSON-RPC 2.0 error codes.
    """
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    SERVER_ERROR_START = -32099
    SERVER_ERROR_END = -32000


class RPCException(Exception):
    """
    Base exception class for RPC-related errors.
    """
    
    def __init__(self, code: int, message: str, data: Optional[Any] = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """
        Convert the exception to a dictionary that follows the JSON-RPC 2.0 error format.
        
        Returns:
            dict: Error object in JSON-RPC 2.0 format
        """
        error_obj = {
            "code": self.code,
            "message": self.message
        }
        
        if self.data is not None:
            error_obj["data"] = self.data
            
        return error_obj


class ParseError(RPCException):
    """
    Exception raised when invalid JSON is received by the server.
    """
    
    def __init__(self, message: str = "Parse error", data: Optional[Any] = None):
        super().__init__(RPCErrorCode.PARSE_ERROR, message, data)


class InvalidRequestError(RPCException):
    """
    Exception raised when the JSON sent is not a valid Request object.
    """
    
    def __init__(self, message: str = "Invalid Request", data: Optional[Any] = None):
        super().__init__(RPCErrorCode.INVALID_REQUEST, message, data)


class MethodNotFoundError(RPCException):
    """
    Exception raised when the method does not exist / is not available.
    """
    
    def __init__(self, message: str = "Method not found", data: Optional[Any] = None):
        super().__init__(RPCErrorCode.METHOD_NOT_FOUND, message, data)


class InvalidParamsError(RPCException):
    """
    Exception raised when invalid method parameter(s) were provided.
    """
    
    def __init__(self, message: str = "Invalid params", data: Optional[Any] = None):
        super().__init__(RPCErrorCode.INVALID_PARAMS, message, data)


class InternalError(RPCException):
    """
    Exception raised when an internal error occurred.
    """
    
    def __init__(self, message: str = "Internal error", data: Optional[Any] = None):
        super().__init__(RPCErrorCode.INTERNAL_ERROR, message, data)


def handle_rpc_error(func):
    """
    Decorator to handle exceptions and convert them to JSON-RPC 2.0 compliant errors.
    """
    import functools
    import logging
    
    logger = logging.getLogger(__name__)
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except RPCException as e:
            # Re-raise RPC exceptions as they're already properly formatted
            logger.error(f"RPC error in {func.__name__}: {e.message} (Code: {e.code})")
            raise
        except Exception as e:
            # Convert unexpected exceptions to internal error
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
            raise InternalError(f"Internal error in {func.__name__}: {str(e)}")
    
    return wrapper


def handle_rpc_error_sync(func):
    """
    Decorator to handle exceptions and convert them to JSON-RPC 2.0 compliant errors for sync functions.
    """
    import functools
    import logging
    
    logger = logging.getLogger(__name__)
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except RPCException as e:
            # Re-raise RPC exceptions as they're already properly formatted
            logger.error(f"RPC error in {func.__name__}: {e.message} (Code: {e.code})")
            raise
        except Exception as e:
            # Convert unexpected exceptions to internal error
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}", exc_info=True)
            raise InternalError(f"Internal error in {func.__name__}: {str(e)}")
    
    return wrapper