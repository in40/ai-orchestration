#!/usr/bin/env python3

"""
Registry Validation Script
Validates the catalog entry against MCP server catalog schema
"""

import yaml
import json
from pathlib import Path
from typing import Dict, Any, List

def validate_catalog_entry(catalog_file: str) -> bool:
    """Validate the catalog entry against expected schema"""
    
    # Expected schema for MCP catalog entries
    expected_fields = {
        'id': str,
        'name': str,
        'category': str,
        'description': str,
        'auth_type': str,
        'provider': str,
        'tags': list,
        'transport': str,
        'port': int,
        'capabilities': dict
    }
    
    required_fields = ['id', 'name', 'category', 'description', 'auth_type', 'provider', 'tags', 'transport', 'port']
    
    try:
        with open(catalog_file, 'r') as f:
            catalog_data = yaml.safe_load(f)
        
        print(f"Loaded catalog entry: {catalog_data.get('name', 'Unknown')}")
        
        # Check required fields
        missing_fields = []
        for field in required_fields:
            if field not in catalog_data:
                missing_fields.append(field)
        
        if missing_fields:
            print(f"❌ Missing required fields: {missing_fields}")
            return False
        
        # Validate field types
        type_errors = []
        for field, expected_type in expected_fields.items():
            if field in catalog_data:
                if not isinstance(catalog_data[field], expected_type):
                    type_errors.append(f"{field}: expected {expected_type.__name__}, got {type(catalog_data[field]).__name__}")
        
        if type_errors:
            print(f"❌ Type errors: {type_errors}")
            return False
        
        # Validate specific values
        valid_transports = ['STREAMABLEHTTP', 'HTTP', 'STDIO']
        if catalog_data['transport'] not in valid_transports:
            print(f"❌ Invalid transport: {catalog_data['transport']}. Valid: {valid_transports}")
            return False
        
        if catalog_data['port'] < 1 or catalog_data['port'] > 65535:
            print(f"❌ Invalid port: {catalog_data['port']}")
            return False
        
        # Validate capabilities structure
        capabilities = catalog_data.get('capabilities', {})
        if not isinstance(capabilities, dict):
            print("❌ Capabilities must be a dictionary")
            return False
        
        # Check for required capability types
        required_caps = ['tools', 'resources', 'prompts']
        for cap_type in required_caps:
            if cap_type not in capabilities:
                print(f"⚠️  Missing capability type: {cap_type}")
        
        print("✅ Catalog entry validation passed!")
        return True
        
    except yaml.YAMLError as e:
        print(f"❌ YAML parsing error: {e}")
        return False
    except FileNotFoundError:
        print(f"❌ Catalog file not found: {catalog_file}")
        return False
    except Exception as e:
        print(f"❌ Validation error: {e}")
        return False

def main():
    """Main validation function"""
    catalog_file = "catalog_entry.yaml"
    
    print("🔍 Validating MCP Server Catalog Entry")
    print("=" * 50)
    
    if not Path(catalog_file).exists():
        print(f"❌ Catalog file {catalog_file} does not exist")
        return False
    
    is_valid = validate_catalog_entry(catalog_file)
    
    print("=" * 50)
    if is_valid:
        print("🎉 Catalog entry is valid and ready for registration!")
        return True
    else:
        print("💥 Catalog entry validation failed!")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)