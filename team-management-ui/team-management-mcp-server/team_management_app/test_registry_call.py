#!/usr/bin/env python3
"""
Test script to debug the registry API call directly
"""
import requests
import json

def test_registry_call():
    """Test the registry call directly"""
    print("Testing registry call directly...")
    
    try:
        response = requests.post(
            'http://localhost:3031/mcp',
            json={
                "jsonrpc": "2.0",
                "id": "list_services_debug",
                "method": "registry/list",
                "params": {}
            },
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Registry response status: {response.status_code}")
        
        if response.status_code == 200:
            registry_data = response.json()
            print(f"Registry response keys: {list(registry_data.keys())}")
            
            if 'result' in registry_data:
                services = registry_data['result'].get('services', [])
                print(f"Number of services in registry: {len(services)}")
                
                for i, service in enumerate(services):
                    print(f"Service {i+1}: {service.get('name', 'Unknown')} (ID: {service.get('id', 'Unknown')})")
                    
                    # Check if this service should be included as an AI agent
                    service_name = service.get('name', '')
                    service_id = service.get('id', '')
                    
                    # Skip the registry service itself
                    if 'registry' in service_id.lower() or 'registry' in service_name.lower():
                        print("  -> SKIPPED (Registry service)")
                        continue
                    
                    # Identify AI agents by checking if they represent specialized team roles
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
                    
                    print(f"  -> Should be included as AI agent: {is_ai_agent}")
            else:
                print("No 'result' key in registry response")
                print(f"Full response: {registry_data}")
        else:
            print(f"Registry call failed with status {response.status_code}")
            print(f"Response text: {response.text}")
            
    except Exception as e:
        print(f"Error in registry call: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_registry_call()