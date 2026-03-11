#!/usr/bin/env python3
import sys
import re
sys.path.insert(0, '/root/qwen/base/mcp-std-coder/mcp-vibe-coding-agent')

from dependencies.vibe_coder import extract_code_from_llm_response, detect_language_from_response

# Simulate actual LLM response (based on what we're seeing in stored files)
llm_response = '''```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Test</title>
</head>
<body>
    <h1>Hello World</h1>
</body>
</html>
```'''

print("Testing extract_code_from_llm_response()")
print("=" * 60)
print(f"Input length: {len(llm_response)} chars")
print(f"Input starts with: {llm_response[:20]}...")
print()

extracted = extract_code_from_llm_response(llm_response, preferred_language='html')
print(f"Extracted length: {len(extracted)} chars")
print(f"Extracted starts with: {extracted[:50]}...")
print()

if extracted.startswith('```'):
    print("❌ FAIL: Extraction returned markdown markers!")
    print(f"   First 10 chars: {extracted[:10]}")
else:
    print("✅ PASS: Clean code extracted!")

print()
print("Testing detect_language_from_response()")
detected = detect_language_from_response(llm_response)
print(f"Detected language: {detected}")
