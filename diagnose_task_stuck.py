#!/usr/bin/env python3
"""
Diagnostic Script: Investigate Why Tasks Are Stuck at in_progress

This script checks:
1. IT Lead server status and configuration
2. Implementation Engineer agent registration
3. Agent endpoint connectivity
4. Tool availability on implementation-engineer
5. Database task status
"""
import requests
import json
import sys

# Configuration
IT_LEAD_HOST = "127.0.0.1"
IT_LEAD_PORT = 3061
IMPL_ENG_HOST = "127.0.0.1"
IMPL_ENG_PORT = 3062  # Expected implementation-engineer port
REGISTRY_HOST = "127.0.0.1"
REGISTRY_PORT = 3031

def check_registry():
    """Check MCP Registry for registered agents"""
    print("\n" + "="*60)
    print("1. CHECKING MCP REGISTRY")
    print("="*60)
    
    try:
        response = requests.get(f"http://{REGISTRY_HOST}:{REGISTRY_PORT}/api/services", timeout=5)
        if response.status_code == 200:
            services = response.json()
            print(f"✅ Registry is running at {REGISTRY_HOST}:{REGISTRY_PORT}")
            print(f"   Found {len(services)} registered service(s):")
            
            impl_eng_found = False
            for svc in services:
                name = svc.get("name", "Unknown")
                endpoint = svc.get("endpoint", "N/A")
                print(f"   - {name}")
                print(f"     Endpoint: {endpoint}")
                
                if "implementation" in name.lower():
                    impl_eng_found = True
                    print(f"     ⭐ Implementation Engineer FOUND!")
                    
            if not impl_eng_found:
                print(f"   ❌ Implementation Engineer NOT registered!")
                return False
            return True
        else:
            print(f"❌ Registry returned status {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"❌ Cannot reach MCP Registry: {e}")
        return False


def check_it_lead_server():
    """Check IT Lead server health and configuration"""
    print("\n" + "="*60)
    print("2. CHECKING IT LEAD SERVER")
    print("="*60)
    
    try:
        # Try to get tools list
        response = requests.post(
            f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp",
            json={
                "jsonrpc": "2.0",
                "id": "check-1",
                "method": "tools/list",
                "params": {}
            },
            timeout=5
        )
        
        if response.status_code == 200:
            print(f"✅ IT Lead server is running at {IT_LEAD_HOST}:{IT_LEAD_PORT}")
            result = response.json()
            tools = result.get("result", {}).get("tools", [])
            print(f"   Available tools: {len(tools)}")
            
            # Check for assign_task tool
            has_assign = any(t.get("name") == "assign_task" for t in tools)
            if has_assign:
                print(f"   ✅ assign_task tool is available")
            else:
                print(f"   ❌ assign_task tool NOT found!")
                
            return True
        else:
            print(f"❌ IT Lead returned status {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"❌ Cannot reach IT Lead server: {e}")
        return False


def check_implementation_engineer():
    """Check Implementation Engineer agent directly"""
    print("\n" + "="*60)
    print("3. CHECKING IMPLEMENTATION ENGINEER AGENT")
    print("="*60)
    
    # Try common ports
    ports_to_try = [3062, 3060, 3063]
    
    for port in ports_to_try:
        try:
            response = requests.post(
                f"http://{IMPL_ENG_HOST}:{port}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "check-impl",
                    "method": "tools/list",
                    "params": {}
                },
                timeout=5
            )
            
            if response.status_code == 200:
                print(f"✅ Implementation Engineer found at port {port}")
                result = response.json()
                tools = result.get("result", {}).get("tools", [])
                print(f"   Available tools: {len(tools)}")
                
                # Check for vibe_code_async
                has_vibe_async = any(t.get("name") == "vibe_code_async" for t in tools)
                has_vibe = any(t.get("name") == "vibe_code" for t in tools)
                has_implement = any(t.get("name") == "implement_feature" for t in tools)
                
                print(f"   - vibe_code_async: {'✅' if has_vibe_async else '❌'}")
                print(f"   - vibe_code: {'✅' if has_vibe else '❌'}")
                print(f"   - implement_feature: {'✅' if has_implement else '❌'}")
                
                if not (has_vibe_async or has_vibe or has_implement):
                    print(f"   ⚠️  WARNING: No coding tools found! Task forwarding will fail.")
                
                return port
            else:
                print(f"⚠️  Port {port} returned status {response.status_code}")
        except requests.RequestException as e:
            print(f"⚠️  Port {port} not responding: {e}")
    
    print(f"❌ Implementation Engineer NOT found on any expected port!")
    return None


def check_task_in_db(task_id):
    """Check task status in database"""
    print("\n" + "="*60)
    print(f"4. CHECKING TASK {task_id} IN DATABASE")
    print("="*60)
    
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="127.0.0.1",
            port=5432,
            database="mcp_registry",
            user="postgres",
            password="postgres"
        )
        cur = conn.cursor()
        
        cur.execute("""
            SELECT task_id, title, status, assigned_to, created_at, metadata
            FROM tasks 
            WHERE task_id LIKE %s
            ORDER BY created_at DESC
            LIMIT 5
        """, (f"%{task_id}%",))
        
        rows = cur.fetchall()
        
        if rows:
            print(f"✅ Found {len(rows)} task(s) matching '{task_id}':")
            for row in rows:
                print(f"\n   Task ID: {row[0]}")
                print(f"   Status: {row[2]}")
                print(f"   Assigned To: {row[3]}")
                print(f"   Created: {row[4]}")
                
                # Parse metadata if JSON
                if row[5]:
                    try:
                        metadata = json.loads(row[5]) if isinstance(row[5], str) else row[5]
                        llm_plan = metadata.get("llm_plan", {})
                        if llm_plan:
                            print(f"   LLM Plan - Primary Agent: {llm_plan.get('primary_agent', 'N/A')}")
                            print(f"   LLM Plan - Tool: {llm_plan.get('tools', {})}")
                    except:
                        pass
        else:
            print(f"❌ No tasks found matching '{task_id}'")
            
        cur.close()
        conn.close()
        
    except ImportError:
        print(f"⚠️  psycopg2 not installed, cannot check database")
    except Exception as e:
        print(f"❌ Database check failed: {e}")


def test_agent_forwarding():
    """Test if IT Lead can forward tasks to Implementation Engineer"""
    print("\n" + "="*60)
    print("5. TESTING AGENT ENDPOINT CONNECTIVITY")
    print("="*60)
    
    # Get agent endpoint from registry
    try:
        response = requests.get(f"http://{REGISTRY_HOST}:{REGISTRY_PORT}/api/services", timeout=5)
        if response.status_code == 200:
            services = response.json()
            
            for svc in services:
                name = svc.get("name", "").lower()
                endpoint = svc.get("endpoint")
                
                if "implementation" in name and endpoint:
                    print(f"   Testing endpoint: {endpoint}")
                    
                    # Try to call the endpoint
                    try:
                        test_response = requests.post(
                            endpoint,
                            json={
                                "jsonrpc": "2.0",
                                "id": "test-1",
                                "method": "tools/call",
                                "params": {
                                    "name": "vibe_code_async",
                                    "arguments": {
                                        "task_description": "test",
                                        "language": "python",
                                        "vibe_level": 1
                                    }
                                }
                            },
                            timeout=10
                        )
                        
                        if test_response.status_code == 200:
                            result = test_response.json()
                            if "error" in result:
                                print(f"   ⚠️  Endpoint responded with error: {result['error']}")
                            else:
                                print(f"   ✅ Endpoint is working!")
                                return True
                        else:
                            print(f"   ❌ Endpoint returned status {test_response.status_code}")
                    except Exception as e:
                        print(f"   ❌ Endpoint call failed: {e}")
                        
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
    
    return False


def main():
    print("\n" + "="*60)
    print("TASK STUCK DIAGNOSTIC TOOL")
    print("Investigating: task-1772835632522")
    print("="*60)
    
    # Run all checks
    registry_ok = check_registry()
    it_lead_ok = check_it_lead_server()
    impl_port = check_implementation_engineer()
    
    # Check database
    check_task_in_db("task-1772835632522")
    
    # Test forwarding
    if registry_ok:
        test_agent_forwarding()
    
    # Summary
    print("\n" + "="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)
    
    issues = []
    
    if not registry_ok:
        issues.append("❌ MCP Registry is not accessible")
    else:
        print("✅ MCP Registry is accessible")
        
    if not it_lead_ok:
        issues.append("❌ IT Lead server is not accessible")
    else:
        print("✅ IT Lead server is accessible")
        
    if not impl_port:
        issues.append("❌ Implementation Engineer agent is NOT running or not accessible")
    else:
        print(f"✅ Implementation Engineer is running on port {impl_port}")
        
    if issues:
        print("\n🚨 IDENTIFIED ISSUES:")
        for issue in issues:
            print(f"  {issue}")
        print("\n💡 RECOMMENDATION:")
        if not impl_port:
            print("  Start the Implementation Engineer MCP server!")
            print("  Example: python -m mcp_vibe_coding_agent.server --port 3062")
        else:
            print("  Check IT Lead server logs for forwarding errors")
    else:
        print("\n✅ All systems appear to be running.")
        print("  Check IT Lead server logs for detailed error messages.")
        print("  The issue may be in the LLM call or task forwarding logic.")


if __name__ == "__main__":
    main()
