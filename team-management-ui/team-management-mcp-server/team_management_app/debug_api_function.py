#!/usr/bin/env python3
"""
Debug script to test the get_team_members function directly
"""
import sys
import os
import json

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Change to the correct directory
os.chdir(os.path.join(os.path.dirname(__file__)))

def test_get_team_members():
    """Test the get_team_members function directly"""
    try:
        # Import the function
        from api_server import get_team_members
        
        # Call the function directly
        result = get_team_members()
        
        print("Result type:", type(result))
        print("Result:", result)
        
        # If result is a Flask response object, get its data
        if hasattr(result, 'get_json'):
            json_data = result.get_json()
            print("JSON data:", json_data)
        elif isinstance(result, tuple) and len(result) >= 2:
            # Likely (json_data, status_code) tuple
            print("Tuple result - data:", result[0])
            print("Status code:", result[1])
        elif isinstance(result, str):
            # String response, try to parse as JSON
            try:
                parsed = json.loads(result)
                print("Parsed JSON:", parsed)
            except json.JSONDecodeError:
                print("String result (not JSON):", result[:200] + ("..." if len(result) > 200 else ""))
        else:
            print("Other result type:", result)
            
    except Exception as e:
        print(f"Error calling get_team_members: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Testing get_team_members function directly...")
    test_get_team_members()