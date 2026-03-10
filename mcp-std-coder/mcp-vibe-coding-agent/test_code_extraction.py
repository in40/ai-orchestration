#!/usr/bin/env python3
"""
Test script for improved code extraction from LLM responses
"""
import sys
sys.path.insert(0, '/root/qwen/base/mcp-std-coder/mcp-vibe-coding-agent')

from dependencies.vibe_coder import extract_code_from_llm_response, detect_language_from_response

def test_html_extraction():
    """Test extraction of HTML code blocks"""
    print("\n=== Test 1: HTML Code Extraction ===")
    
    response = """Sure! Here's a simple Flappy Bird game in HTML:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Flappy Bird</title>
</head>
<body>
    <canvas id="gameCanvas" width="400" height="600"></canvas>
    <script>
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        
        // Game loop
        function gameLoop() {
            // Update and draw game
            requestAnimationFrame(gameLoop);
        }
        gameLoop();
    </script>
</body>
</html>
```

Hope you enjoy this vibe-coded game!"""
    
    extracted = extract_code_from_llm_response(response, preferred_language='html')
    detected = detect_language_from_response(response)
    
    print(f"Detected language: {detected}")
    print(f"Extracted code length: {len(extracted)} chars")
    print(f"Starts with DOCTYPE: {extracted.startswith('<!DOCTYPE html>')}")
    assert detected == 'html', f"Expected 'html', got '{detected}'"
    assert '<!DOCTYPE html>' in extracted, "HTML content not extracted properly"
    print("✅ HTML extraction test passed!")


def test_javascript_extraction():
    """Test extraction of JavaScript code blocks"""
    print("\n=== Test 2: JavaScript Code Extraction ===")
    
    response = """Here's a JavaScript function for you:

```javascript
/**
 * Calculates the Fibonacci sequence
 * @param {number} n - The position in the sequence
 * @returns {number} The Fibonacci number
 */
function fibonacci(n) {
    if (n <= 1) return n;
    return fibonacci(n - 1) + fibonacci(n - 2);
}

// Vibe check: This function is feeling recursive! 🌀
console.log(fibonacci(10));
```

Let me know if you need any modifications!"""
    
    extracted = extract_code_from_llm_response(response, preferred_language='javascript')
    detected = detect_language_from_response(response)
    
    print(f"Detected language: {detected}")
    print(f"Extracted code length: {len(extracted)} chars")
    print(f"Contains function keyword: {'function fibonacci' in extracted}")
    assert detected == 'javascript', f"Expected 'javascript', got '{detected}'"
    assert 'function fibonacci' in extracted, "JavaScript content not extracted properly"
    print("✅ JavaScript extraction test passed!")


def test_python_extraction():
    """Test extraction of Python code blocks"""
    print("\n=== Test 3: Python Code Extraction ===")
    
    response = '''Here's a Python script:

```python
#!/usr/bin/env python3
"""
A simple Python script with a vibe check
"""

def greet(name):
    return f"Hello, {name}! 🌟"

if __name__ == "__main__":
    print(greet("World"))
```

This should work perfectly!'''
    
    extracted = extract_code_from_llm_response(response, preferred_language='python')
    detected = detect_language_from_response(response)
    
    print(f"Detected language: {detected}")
    print(f"Extracted code length: {len(extracted)} chars")
    print(f"Contains def greet: {'def greet' in extracted}")
    assert detected == 'python', f"Expected 'python', got '{detected}'"
    assert 'def greet' in extracted, "Python content not extracted properly"
    print("✅ Python extraction test passed!")


def test_multiple_blocks():
    """Test extraction when multiple code blocks are present"""
    print("\n=== Test 4: Multiple Code Blocks ===")
    
    response = """Here's a complete web page:

First, the HTML structure:

```html
<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body><h1>Hello</h1></body>
</html>
```

Now the CSS styling:

```css
body {
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 20px;
}
```

And finally the JavaScript:

```javascript
console.log('Page loaded');
```

All done!"""
    
    # Should extract HTML when preferred language is html
    extracted_html = extract_code_from_llm_response(response, preferred_language='html')
    assert '<!DOCTYPE html>' in extracted_html, "HTML block not found"
    
    # Should extract CSS when preferred language is css
    extracted_css = extract_code_from_llm_response(response, preferred_language='css')
    assert 'font-family: Arial' in extracted_css, "CSS block not found"
    
    # Should extract JavaScript when preferred language is javascript
    extracted_js = extract_code_from_llm_response(response, preferred_language='javascript')
    assert 'console.log' in extracted_js, "JavaScript block not found"
    
    print("✅ Multiple code blocks test passed!")


def test_no_language_block():
    """Test extraction when no language is specified in code block"""
    print("\n=== Test 5: No Language Specified ===")
    
    response = """Here's some code:

```
def hello():
    print("Hello, World!")
```

Simple and clean!"""
    
    extracted = extract_code_from_llm_response(response)
    
    print(f"Extracted code length: {len(extracted)} chars")
    print(f"Contains def hello: {'def hello' in extracted}")
    assert 'def hello' in extracted, "Code block without language not extracted"
    print("✅ No language block test passed!")


def test_fallback_detection():
    """Test language detection from content"""
    print("\n=== Test 6: Fallback Language Detection ===")
    
    # HTML detection
    html_response = "<html><head><title>Test</title></head><body></body></html>"
    assert detect_language_from_response(html_response) == 'html', "HTML not detected"
    
    # Python detection
    python_response = "def main():\n    print('Hello')\n\nif __name__ == '__main__':\n    main()"
    assert detect_language_from_response(python_response) == 'python', "Python not detected"

    # JavaScript detection
    js_response = "function test() {\n    const x = 1;\n    console.log(x);\n}"
    assert detect_language_from_response(js_response) == 'javascript', "JavaScript not detected"

    print("✅ Fallback detection test passed!")


def test_cleaning_natural_language():
    """Test that natural language is cleaned from code blocks"""
    print("\n=== Test 7: Natural Language Cleaning ===")

    # Test with natural language that should be cleaned
    response = """Sure! Here's the code you requested.

```python
# Here's the code you requested. This function does X and Y.
def greet(name):
    return f"Hello, {name}!"

# I hope this helps! Let me know if you need modifications.
```

Enjoy coding!"""

    extracted = extract_code_from_llm_response(response, preferred_language='python')
    
    # Should contain the actual code
    assert 'def greet(name):' in extracted, "Code function not found"
    
    # Should NOT contain the natural language phrases
    assert "Here's the code you requested" not in extracted, "Intro text not cleaned"
    assert "I hope this helps" not in extracted, "Outro text not cleaned"
    
    print(f"Extracted code:\n{extracted}")
    print("✅ Natural language cleaning test passed!")


def test_unclosed_code_block():
    """Test extraction of unclosed code blocks (LLM doesn't close the block)"""
    print("\n=== Test 8: Unclosed Code Block ===")

    # LLM sometimes doesn't close the code block
    response = """Here's your code:

```html
<!DOCTYPE html>
<html>
<head><title>Test</title></head>
<body><h1>Unclosed block</h1></body>
</html>
"""

    extracted = extract_code_from_llm_response(response, preferred_language='html')
    
    # Should extract the code without the opening markers
    assert '<!DOCTYPE html>' in extracted, "HTML content not extracted"
    assert not extracted.startswith('```'), "Should not start with backticks"
    
    print(f"Extracted code length: {len(extracted)} chars")
    print("✅ Unclosed code block test passed!")


if __name__ == "__main__":
    print("Testing improved code extraction from LLM responses...")
    print("=" * 60)

    test_html_extraction()
    test_javascript_extraction()
    test_python_extraction()
    test_multiple_blocks()
    test_no_language_block()
    test_fallback_detection()
    test_cleaning_natural_language()
    test_unclosed_code_block()

    print("\n" + "=" * 60)
    print("✅ All tests passed!")
    print("\nSummary:")
    print("- Code extraction now supports language-specific markdown blocks")
    print("- Language detection works from both code blocks and content")
    print("- Multiple code blocks can be extracted based on preferred language")
    print("- Natural language cleaning removes intro/outro text from code blocks")
    print("- Handles unclosed code blocks (LLM doesn't close ```)")
    print("- Fallback to full response if no code blocks found")
