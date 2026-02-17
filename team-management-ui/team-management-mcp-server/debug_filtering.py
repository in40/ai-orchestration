#!/usr/bin/env python3
"""
Debug script to test the filtering logic
"""

# Simulate the service data from the registry
services = [
    {
        "id": "server-127.0.0.1-3060",
        "name": "MCP Server on 127.0.0.1:3060",
        "description": "MCP server providing services on 127.0.0.1:3060",
        "endpoint": "http://127.0.0.1:3060/mcp"
    },
    {
        "id": "registry-127.0.0.1:3031",
        "name": "MCP Service Registry",
        "description": "Central registry for MCP services",
        "endpoint": "http://127.0.0.1:3031"
    },
    {
        "id": "requirement-engineer-server-127.0.0.1-3062",
        "name": "Requirement Engineer MCP Server on 127.0.0.1:3062",
        "description": "Specialized MCP server for requirements engineering tasks on 127.0.0.1:3062",
        "endpoint": "http://127.0.0.1:3062/mcp"
    },
    {
        "id": "team-management-server-127.0.0.1-3063",
        "name": "Team Management MCP Server on 127.0.0.1:3063",
        "description": "Team management server providing team management services on 127.0.0.1:3063",
        "endpoint": "http://127.0.0.1:3063/mcp"
    }
]

print("Testing filtering logic...")
print("="*50)

for service in services:
    service_id = service.get('id', '')
    service_name = service.get('name', '')
    service_desc = service.get('description', '')
    
    print(f"Service: {service_name}")
    print(f"  ID: {service_id}")
    
    # Check if it's a registry service (should be skipped)
    is_registry = 'registry' in service_id.lower() or 'registry' in service_name.lower()
    print(f"  Is Registry: {is_registry}")
    
    if is_registry:
        print("  -> SKIPPED (Registry)")
        print()
        continue
    
    # Apply the filtering logic
    service_name_lower = service_name.lower()
    is_ai_agent = (
        'it lead' in service_name_lower or
        ('requirement' in service_name_lower and 'engineer' in service_name_lower) or
        ('implementation' in service_name_lower and 'engineer' in service_name_lower) or
        ('software' in service_name_lower and 'architect' in service_name_lower) or
        ('code' in service_name_lower and 'review' in service_name_lower) or
        'qa' in service_name_lower or
        ('test' in service_name_lower and 'engineer' in service_name_lower) or
        ('security' in service_name_lower and 'engineer' in service_name_lower) or
        'devops' in service_name_lower or
        ('release' in service_name_lower and 'engineer' in service_name_lower) or
        ('technical' in service_name_lower and 'writer' in service_name_lower) or
        'team management' in service_name_lower  # This server itself
    )
    
    print(f"  Matches AI Agent Criteria: {is_ai_agent}")
    
    # Check infrastructure exclusion
    is_not_infrastructure = (
        'registry' not in service_id.lower() and
        'MCP Service Registry' not in service_name
    )
    
    print(f"  Not Infrastructure: {is_not_infrastructure}")
    
    # Final decision
    if is_ai_agent and is_not_infrastructure:
        print("  -> INCLUDED as AI Agent")
    else:
        print("  -> EXCLUDED")
    
    print("-" * 30)

print("Done!")