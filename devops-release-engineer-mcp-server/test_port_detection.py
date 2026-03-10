#!/usr/bin/env python3
"""
Test script to verify port detection logic in DevOps Engineer
"""
import re

def detect_port(content: str) -> int:
    """Detect PORT from generated code - same logic as in server_handlers.py"""
    container_port = 5000  # Default fallback
    port_patterns = [
        r'PORT\s*=\s*(\d+)',           # PORT = 8080
        r'port\s*=\s*(\d+)',           # port = 8080
        r'PORT\s*=\s*int\(os\.environ\.get\(["\']PORT["\']\s*,\s*(\d+)\)\)',  # PORT = int(os.environ.get("PORT", 8080))
        r'server\.listen\((\d+)\)',    # server.listen(3000) - Node.js style
        r'app\.run\(.*port\s*=\s*(\d+)',  # app.run(port=5000)
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
    
    return container_port


# Test cases
test_cases = [
    # Test 1: Standard PORT = 8080
    ("""
class NexusHandler(http.server.SimpleHTTPRequestHandler):
    pass

PORT = 8080

if __name__ == "__main__":
    run_server()
""", 8080, "PORT = 8080"),

    # Test 2: Default PORT = 5000
    ("""
PORT = 5000

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        httpd.serve_forever()
""", 5000, "PORT = 5000"),

    # Test 3: Environment variable with default
    ("""
import os
PORT = int(os.environ.get("PORT", 3000))

if __name__ == "__main__":
    run_server()
""", 3000, "PORT = int(os.environ.get('PORT', 3000))"),

    # Test 4: No port specified (should default to 5000)
    ("""
class Handler(http.server.SimpleHTTPRequestHandler):
    pass

if __name__ == "__main__":
    with socketserver.TCPServer(("", 5000), Handler) as httpd:
        httpd.serve_forever()
""", 5000, "No PORT variable (default)"),

    # Test 5: lowercase port = 9000
    ("""
port = 9000

if __name__ == "__main__":
    run_server()
""", 9000, "port = 9000 (lowercase)"),

    # Test 6: Flask app.run with port
    ("""
from flask import Flask
app = Flask(__name__)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
""", 5000, "app.run(port=5000)"),
]

print("=" * 60)
print("Port Detection Test Suite")
print("=" * 60)

passed = 0
failed = 0

for i, (code, expected_port, description) in enumerate(test_cases, 1):
    print(f"\nTest {i}: {description}")
    print("-" * 40)
    detected = detect_port(code)
    if detected == expected_port:
        print(f"✅ PASS: Detected {detected}, expected {expected_port}")
        passed += 1
    else:
        print(f"❌ FAIL: Detected {detected}, expected {expected_port}")
        failed += 1

print("\n" + "=" * 60)
print(f"Results: {passed} passed, {failed} failed")
print("=" * 60)

if failed == 0:
    print("✅ All tests passed!")
    exit(0)
else:
    print("❌ Some tests failed!")
    exit(1)
