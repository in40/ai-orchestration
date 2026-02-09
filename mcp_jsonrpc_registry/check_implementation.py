#!/usr/bin/env python3
"""Simple script to check if the implementation structure is correct."""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_imports():
    """Check if all modules can be imported without errors."""
    print("Checking module imports...")
    
    try:
        from src.models.server import ServerCapabilities, RegisteredServer, RegisterServerRequest
        print("✓ Models imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import models: {e}")
        return False
    
    try:
        from src.models.database import DBRegisteredServer
        print("✓ Database models imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import database models: {e}")
        return False
    
    try:
        from src.services.database import DatabaseService
        print("✓ Database service imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import database service: {e}")
        return False
    
    try:
        from src.services.health_monitor import HealthMonitorService
        print("✓ Health monitor service imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import health monitor service: {e}")
        return False
    
    try:
        from src.server.registry_server import RegistryServer
        print("✓ Registry server imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import registry server: {e}")
        return False
    
    try:
        from config.settings import settings
        print("✓ Settings imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import settings: {e}")
        return False
    
    return True

def check_models():
    """Check if models work correctly."""
    print("\nChecking model functionality...")
    
    try:
        # Test ServerCapabilities
        from src.models.server import ServerCapabilities
        caps = ServerCapabilities(
            resources=True,
            tools=True,
            prompts=False,
            roots=False,
            sampling=True
        )
        assert caps.resources == True
        assert caps.tools == True
        assert caps.prompts == False
        print("✓ ServerCapabilities model works correctly")
    except Exception as e:
        print(f"✗ ServerCapabilities model failed: {e}")
        return False
    
    try:
        # Test RegisterServerRequest
        from src.models.server import ServerCapabilities, RegisterServerRequest
        caps = ServerCapabilities(resources=True, tools=True)
        req = RegisterServerRequest(
            name="Test Server",
            description="A test server",
            endpoint="http://localhost:8000",
            capabilities=caps,
            metadata={"version": "1.0.0"},
            tags=["test", "utility"]
        )
        assert req.name == "Test Server"
        assert req.metadata["version"] == "1.0.0"
        print("✓ RegisterServerRequest model works correctly")
    except Exception as e:
        print(f"✗ RegisterServerRequest model failed: {e}")
        return False
    
    return True

def check_settings():
    """Check if settings work correctly."""
    print("\nChecking settings...")
    
    try:
        from config.settings import settings
        assert hasattr(settings, 'database_url')
        assert hasattr(settings, 'http_port')
        print("✓ Settings work correctly")
    except Exception as e:
        print(f"✗ Settings failed: {e}")
        return False
    
    return True

def main():
    """Run all checks."""
    print("MCP Server Registry Implementation Check")
    print("=" * 40)
    
    success = True
    success &= check_imports()
    success &= check_models()
    success &= check_settings()
    
    print("\n" + "=" * 40)
    if success:
        print("✓ All checks passed! Implementation structure is correct.")
        return 0
    else:
        print("✗ Some checks failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())