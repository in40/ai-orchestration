# Code Extraction Improvement for LLM Responses

## Problem

When the Implementation Engineer receives code from the LLM, the response often contains:
- Explanatory text before/after the code
- Multiple code blocks for different files
- Conversational text mixed with code

Previously, the code extraction was basic and didn't properly handle:
- Language-specific markdown code blocks (```html, ```javascript, etc.)
- Multiple code blocks in a single response
- Automatic language detection from the response

## Solution

Enhanced the code extraction and language detection in `vibe_coder.py`:

### 1. Improved `extract_code_from_llm_response()`

**Before:**
```python
def extract_code_from_llm_response(response: str) -> str:
    code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', response, re.DOTALL)
    if code_blocks:
        return code_blocks[0].strip()
    return response.strip()
```

**After:**
```python
def extract_code_from_llm_response(response: str, preferred_language: Optional[str] = None) -> str:
    """
    Extract code from LLM response with language-aware extraction.
    
    Features:
    - Supports language-specific code blocks (```html, ```javascript, etc.)
    - Can prefer specific language when multiple blocks exist
    - Falls back to full response if no code blocks found
    """
    code_block_pattern = r'```(\w+)?\n(.*?)```'
    matches = re.findall(code_block_pattern, response, re.DOTALL)
    
    if matches:
        # If preferred language specified, try to find matching block
        if preferred_language:
            for lang, code in matches:
                if lang and lang.lower() == preferred_language.lower():
                    return code.strip()
        
        # Prefer blocks with language specification
        for lang, code in matches:
            if lang:
                return code.strip()
        
        # Fallback to first code block
        return matches[0][1].strip()
    
    return response.strip()
```

### 2. New `detect_language_from_response()`

```python
def detect_language_from_response(response: str) -> str:
    """
    Detect programming language from LLM response.
    
    Strategy:
    1. Check language identifier in code blocks (```html)
    2. Fallback to content analysis (HTML tags, Python keywords, etc.)
    """
    # Check code block language tags
    lang_pattern = r'```(\w+)\n'
    matches = re.findall(lang_pattern, response)
    if matches:
        return matches[0].lower()
    
    # Content-based detection
    response_lower = response.lower()
    if '<!doctype html' in response_lower or '<html' in response_lower:
        return 'html'
    if 'function(' in response_lower or 'const ' in response_lower:
        return 'javascript'
    if 'def ' in response_lower or 'import ' in response_lower:
        return 'python'
    # ... more languages
    
    return 'python'  # default
```

### 3. Updated `git_push_llm_response()`

Now uses both extraction and detection:

```python
def git_push_llm_response(task_id: str, llm_response: str, language: str = "python"):
    # Extract code with preferred language hint
    code = extract_code_from_llm_response(llm_response, preferred_language=language)
    
    # Detect actual language from response
    detected_language = detect_language_from_response(llm_response)
    
    # Use detected language if more specific than default
    if language.lower() in ['python', 'code'] or detected_language != 'python':
        language = detected_language
    
    # Save with correct file extension
    extension = language_extensions.get(language.lower(), ".py")
    filename = f"result{extension}"
    filepath.write_text(code)
```

### 4. Enhanced LLM Prompt

Updated `create_vibe_code_prompt()` to instruct the LLM:

```
## IMPORTANT OUTPUT FORMAT INSTRUCTIONS:

1. **Wrap your code in a markdown code block with the language specified**:
   - For HTML: Use ```html
   - For JavaScript: Use ```javascript or ```js
   - For Python: Use ```python
   - For CSS: Use ```css
   - [etc.]

2. **Example format**:
   ```html
   // Your complete, working code here
   ```

3. **Include only the code in the code block** - do not include explanations inside.

4. **You can add explanations BEFORE or AFTER the code block**.

5. Include a short 'vibe check' comment inside the code.
```

## Examples

### HTML Game Example

**LLM Response:**
```
Sure! Here's a Flappy Bird game in HTML:

```html
<!DOCTYPE html>
<html>
<head><title>Flappy Bird</title></head>
<body>
    <canvas id="gameCanvas"></canvas>
    <script>
        // Game code here
    </script>
</body>
</html>
```

Enjoy the game!
```

**Extraction Result:**
- ✅ Extracts only the HTML code (no explanatory text)
- ✅ Detects language as 'html'
- ✅ Saves as `result.html`

### Multiple Code Blocks

**LLM Response:**
```
Here's a complete web app:

```html
<!DOCTYPE html>
<html>...</html>
```

```css
body { margin: 0; }
```

```javascript
console.log('loaded');
```
```

**Extraction Result:**
- With `preferred_language='html'`: Extracts HTML block
- With `preferred_language='css'`: Extracts CSS block
- With `preferred_language='javascript'`: Extracts JS block

## Testing

Run the test suite:

```bash
cd /root/qwen/base/mcp-std-coder/mcp-vibe-coding-agent
python3 test_code_extraction.py
```

**Test Results:**
```
✅ HTML extraction test passed!
✅ JavaScript extraction test passed!
✅ Python extraction test passed!
✅ Multiple code blocks test passed!
✅ No language block test passed!
✅ Fallback detection test passed!
```

## Benefits

1. **Cleaner Code Files**: Only code is saved, no conversational text
2. **Correct File Extensions**: HTML files get `.html`, JS files get `.js`, etc.
3. **Multi-Language Support**: Works with any programming language
4. **Robust Detection**: Falls back to content analysis if no language tags
5. **Preferred Language**: Can extract specific blocks from multi-language responses

## Files Modified

- `/root/qwen/base/mcp-std-coder/mcp-vibe-coding-agent/dependencies/vibe_coder.py`
  - Enhanced `extract_code_from_llm_response()`
  - Added `detect_language_from_response()`
  - Updated `git_push_llm_response()`
  - Enhanced `create_vibe_code_prompt()`

- `/root/qwen/base/mcp-std-coder/mcp-vibe-coding-agent/test_code_extraction.py` (new)
  - Comprehensive test suite for code extraction

## Integration

The improvements are automatically used by:
- `vibe_code_async` tool
- `vibe_code` tool
- Any code that calls `git_push_llm_response()`

No changes required in calling code - the improvements are backward compatible.
