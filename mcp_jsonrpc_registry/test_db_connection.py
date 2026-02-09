#!/usr/bin/env python3
"""
Simple script to test database connection for MCP Server Registry
"""

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings

def test_db_connection():
    print(f"Testing database connection...")
    print(f"Database URL: {settings.database_url}")
    
    try:
        # Create engine and test connection
        engine = create_engine(settings.database_url)
        
        # Try to connect
        with engine.connect() as connection:
            print("✓ Successfully connected to the database!")
            
            # Test by executing a simple query
            from sqlalchemy import text
            result = connection.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"✓ PostgreSQL version: {version[:50]}...")
            
        return True
        
    except SQLAlchemyError as e:
        print(f"✗ Database connection failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_db_connection()
    if not success:
        sys.exit(1)
    print("\n✓ Database connection test passed!")