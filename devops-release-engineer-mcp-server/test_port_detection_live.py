#!/usr/bin/env python3
"""Test port detection on actual result.py from task-1773150833618"""
import re
import subprocess
import os

# Simulate what DevOps does
git_url = "ssh://sorokin@192.168.51.187/home/sorokin/mcp-results/tree/main/results/afc3f045-9030-4c31-9942-f91b74c1a7bc/result.py"
task_id = "test-port-detection"

# Extract UUID
uuid_match = re.search(r'/results/([a-f0-9-]+)/', git_url)
result_uuid = uuid_match.group(1)
print(f"UUID: {result_uuid}")

# Extract git repo URL
if "/tree/main/" in git_url:
    git_repo_url = git_url.split("/tree/main/")[0] + ".git"
else:
    git_repo_url = "ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git"

print(f"Git repo: {git_repo_url}")

# Clone repo
git_workdir = f"/tmp/git-fetch-{task_id}"
subprocess.run(["rm", "-rf", git_workdir], check=True)
subprocess.run(["git", "clone", "--depth", "1", git_repo_url, git_workdir], 
               check=True, capture_output=True, timeout=30)
print(f"✅ Cloned repo to {git_workdir}")

# Read result.py
result_file = os.path.join(git_workdir, "results", result_uuid, "result.py")
with open(result_file, 'r') as f:
    content = f.read()

print(f"✅ Read result.py ({len(content)} bytes)")

# Detect PORT
container_port = 5000  # Default fallback
port_patterns = [
    r'PORT\s*=\s*(\d+)',
    r'port\s*=\s*(\d+)',
    r'PORT\s*=\s*int\(os\.environ\.get\(["\']PORT["\']\s*,\s*(\d+)\)\)',
    r'server\.listen\((\d+)\)',
    r'app\.run\(.*port\s*=\s*(\d+)',
]

for pattern in port_patterns:
    port_match = re.search(pattern, content)
    if port_match:
        detected_port = int(port_match.group(1))
        print(f"✅ Detected PORT={detected_port} from pattern: {pattern}")
        container_port = detected_port
        break

if container_port != 5000:
    print(f"⚠️  Non-standard port detected: {container_port} (default is 5000)")
else:
    print(f"ℹ️  Using default PORT=5000 (no custom port detected)")

# Show the relevant lines from result.py
print("\n--- PORT related lines from result.py ---")
for i, line in enumerate(content.split('\n'), 1):
    if 'PORT' in line or 'port' in line:
        print(f"  Line {i}: {line.strip()}")

# Cleanup
subprocess.run(["rm", "-rf", git_workdir])

print(f"\n✅ Port detection test complete!")
