#!/usr/bin/env python3
"""
Test script to debug the filtering logic in the API server
"""

import requests
import json

# Replicate the exact logic from the API server
def test_filtering_logic():
    # Get services from registry
    response = requests.post(
        'http://localhost:3031/mcp',
        json={
            "jsonrpc": "2.0",
            "id": "list_services",
            "method": "registry/list",
            "params": {}
        },
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        registry_data = response.json()
        services = registry_data.get('result', {}).get('services', [])
        
        print(f"Total services in registry: {len(services)}")
        
        # Filter out the registry itself and get only AI agents
        ai_agents = []
        for service in services:
            service_id = service.get('id', '')
            service_name = service.get('name', '')
            service_desc = service.get('description', '')
            
            print(f"Processing service: {service_name} (ID: {service_id})")
            
            # Skip the registry service itself
            is_registry = 'registry' in service_id.lower() or 'registry' in service_name.lower()
            print(f"  Is registry: {is_registry}")
            
            if is_registry:
                print("  -> SKIPPED (Registry)")
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
            
            print(f"  Matches AI agent criteria: {is_ai_agent}")
            
            # Check infrastructure exclusion
            is_not_infrastructure = (
                'registry' not in service_id.lower() and
                'MCP Service Registry' not in service_name
            )
            
            print(f"  Not infrastructure: {is_not_infrastructure}")
            
            # Final decision
            if is_ai_agent and is_not_infrastructure:
                print("  -> INCLUDED as AI Agent")
                
                agent = {
                    'id': service.get('id', ''),
                    'name': service.get('name', 'Unknown Agent'),
                    'email': f"{service.get('id', 'unknown')}@mcp.local",
                    'role': extract_role_from_name(service.get('name', '')),
                    'skills': extract_skills_from_capabilities(service.get('capabilities', {})),
                    'availability': 'online',  # All registered agents are considered available
                    'description': service.get('description', ''),
                    'endpoint': service.get('endpoint', ''),
                    'capabilities': service.get('capabilities', {}),
                    'registered_at': service.get('registered_at'),
                    'last_seen': service.get('last_seen')
                }
                ai_agents.append(agent)
            else:
                print("  -> EXCLUDED")
            
            print("  ---")
        
        print(f"\nFinal result: {len(ai_agents)} AI agents identified")
        for agent in ai_agents:
            print(f"  - {agent['name']} (ID: {agent['id']})")
        
        return ai_agents
    else:
        print(f"Failed to get registry data: {response.status_code}")
        return []

def extract_role_from_name(name):
    """Extract role from service name"""
    if 'IT Lead' in name:
        return 'IT Lead Agent'
    elif 'Requirement' in name or 'Requirement Engineer' in name:
        return 'Requirement Engineer Agent'
    elif 'Implementation' in name or 'Implementation Engineer' in name:
        return 'Implementation Engineer Agent'
    elif 'Software Architect' in name:
        return 'Software Architect Agent'
    elif 'Code Review' in name or 'Code Reviewer' in name:
        return 'Code Reviewer Agent'
    elif 'QA' in name or 'Test' in name:
        return 'QA/Test Engineer Agent'
    elif 'Security' in name:
        return 'Security Engineer Agent'
    elif 'DevOps' in name or 'Release' in name:
        return 'DevOps/Release Engineer Agent'
    elif 'Technical Writer' in name:
        return 'Technical Writer Agent'
    else:
        return 'AI Agent'

def extract_skills_from_capabilities(capabilities):
    """Extract skills from agent capabilities"""
    skills = []
    if 'tools' in capabilities and isinstance(capabilities['tools'], list):
        # Take first 5 tools as representative skills
        skills.extend(capabilities['tools'][:5])
    if len(skills) == 0:
        skills = ['MCP Communication']
    return skills

if __name__ == "__main__":
    print("Testing the filtering logic that's used in the API server...")
    agents = test_filtering_logic()
    print(f"\nExpected: 2 agents (Requirement Engineer and Team Management)")
    print(f"Actual: {len(agents)} agents")