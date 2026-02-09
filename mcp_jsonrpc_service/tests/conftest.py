"""
Pytest configuration for the MCP server tests.
"""
import pytest
import sys
import os

# Add the src directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up the test environment."""
    # Set any necessary environment variables for testing
    os.environ.setdefault("MCP_LOG_LEVEL", "WARNING")  # Reduce log noise during tests
    
    yield
    
    # Cleanup after tests
    # Remove any test-specific environment variables if needed