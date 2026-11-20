#!/usr/bin/env python3
import re

# Simulated LLM response (like what we saw in the stored file)
response = '''```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
</head>
<body>
  <h1>Flappy Croc</h1>
</body>
</html>
```'''

# Current pattern
code_block_pattern = r'```(\w+)?\n(.*?)```'
matches = re.findall(code_block_pattern, response, re.DOTALL)

print(f"Pattern: {code_block_pattern}")
print(f"Matches found: {len(matches)}")
if matches:
    for lang, code in matches:
        print(f"  Language: '{lang}'")
        print(f"  Code preview: {code[:50]}...")
else:
    print("  No matches!")

# Try improved pattern that handles backticks better
print("\n--- Trying improved pattern ---")
improved_pattern = r'```(\w*)\s*\n(.*?)```'
matches2 = re.findall(improved_pattern, response, re.DOTALL)
print(f"Pattern: {improved_pattern}")
print(f"Matches found: {len(matches2)}")
if matches2:
    for lang, code in matches2:
        print(f"  Language: '{lang}'")
        print(f"  Code preview: {code[:50]}...")
