#!/usr/bin/env python3
"""Test script to reproduce the multiple request issue"""

import subprocess
import time

def run_client_command(cmd):
    """Run a client command and return the output"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

def main():
    print("Testing multiple client requests...")
    
    # Test first request
    print("\n1. First request:")
    cmd1 = "cd /root/qwen/base/mcp-coder/mcp_ai_coding_agent && timeout 15s ./run_ai_coding_agent_client.sh --health"
    rc1, out1, err1 = run_client_command(cmd1)
    print(f"Return code: {rc1}")
    print(f"Output preview: {' RECEIVED' if 'Received response' in out1 else ' NO RESPONSE'}")
    if 'Received response' in out1:
        print("✓ First request succeeded")
    else:
        print("✗ First request failed")
    
    time.sleep(2)  # Brief pause
    
    # Test second request
    print("\n2. Second request:")
    cmd2 = "cd /root/qwen/base/mcp-coder/mcp_ai_coding_agent && timeout 15s ./run_ai_coding_agent_client.sh --health"
    rc2, out2, err2 = run_client_command(cmd2)
    print(f"Return code: {rc2}")
    print(f"Output preview: {' RECEIVED' if 'Received response' in out2 else ' NO RESPONSE'}")
    if 'Received response' in out2:
        print("✓ Second request succeeded")
    else:
        print("✗ Second request failed")
    
    time.sleep(2)  # Brief pause
    
    # Test third request
    print("\n3. Third request:")
    cmd3 = "cd /root/qwen/base/mcp-coder/mcp_ai_coding_agent && timeout 15s ./run_ai_coding_agent_client.sh --health"
    rc3, out3, err3 = run_client_command(cmd3)
    print(f"Return code: {rc3}")
    print(f"Output preview: {' RECEIVED' if 'Received response' in out3 else ' NO RESPONSE'}")
    if 'Received response' in out3:
        print("✓ Third request succeeded")
    else:
        print("✗ Third request failed")

if __name__ == "__main__":
    main()