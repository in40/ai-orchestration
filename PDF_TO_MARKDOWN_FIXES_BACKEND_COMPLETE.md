# ✅ PDF to Markdown Conversion Fixes - Backend Complete

## Fixes Implemented (Backend)

### 1. ✅ LLM Response Cleaning
**File**: `/root/qwen/base/it-lead-mcp-server/web-ui/backend/git_result_storage.py`

**Added Functions**:
- `clean_llm_response(content: str) -> str`: Removes LLM artifacts from Markdown content
- `combine_pages_to_markdown(pages: list) -> str`: Combines multiple PDF pages into single document

**What it cleans**:
- "Here's the markdown..." introductions
- "```markdown" code block wrappers
- "```" closing markers
- "Sure!", "Certainly!" prefixes
- "End of document" markers
- Multiple blank lines (normalized to double newline)
- Trailing whitespace

**Example**:
```
BEFORE (raw LLM response):
"""
Sure! Here's the markdown document you requested:

```markdown
# Title

Content here

```

End of document.
"""

AFTER (cleaned):
"""
# Title

Content here
"""
```

### 2. ✅ Multi-Page PDF Combination
**Function**: `combine_pages_to_markdown(pages)`

**What it does**:
- Sorts pages by page number
- Combines all pages into single Markdown document
- Adds page separators (`---`) between pages
- Adds page number markers (`**Page 2**`)

**Output Format**:
```markdown
# Document Title

Content from page 1...

---

**Page 2**

Content from page 2...

---

**Page 3**

Content from page 3...
```

### 3. ✅ File Extension Handling
**Already Correct**: The `store_document_result()` function already uses:
- `.md` for Markdown documents
- `.txt` for plain text
- `.json` for JSON
- `.html` for HTML
- `.yaml` for YAML

**No changes needed** - files are already stored with correct extensions!

## Remaining Work (Web UI)

### 4. ⏳ Add File Preview Dialog
**File**: `/root/qwen/base/it-lead-mcp-server/web-ui/frontend/src/components/TaskManagement.jsx`

**TODO**:
- Add dialog component to display file content
- Add Markdown rendering (use `react-markdown` library)
- Add button to open preview

### 5. ⏳ Make File Names Clickable
**File**: `/root/qwen/base/it-lead-mcp-server/web-ui/frontend/src/components/TaskManagement.jsx`

**TODO**:
- Add click handler to file names in task history
- Open preview dialog on click

### 6. ⏳ Update Web UI File Filter
**File**: `/root/qwen/base/it-lead-mcp-server/web-ui/frontend/src/components/TaskManagement.jsx`

**TODO**:
- Add filter for `.md` files
- Separate filters for `.txt` and `.md` or combined filter

### 7. ⏳ Backend API for File Content
**File**: `/root/qwen/base/it-lead-mcp-server/web-ui/backend/main.py`

**TODO**:
- Add endpoint to serve file content: `GET /api/tasks/{task_id}/files/{filename}`
- Return file content as text
- Set correct Content-Type for Markdown (`text/markdown` or `text/plain`)

## Testing Checklist

- [ ] Upload PDF document
- [ ] Verify conversion to Markdown
- [ ] Verify LLM introductions are removed
- [ ] Verify multiple pages are combined
- [ ] Verify file is stored as `.md`
- [ ] Verify file appears in Web UI task history
- [ ] Click file name → preview dialog opens
- [ ] Verify Markdown is rendered correctly in preview

## Next Steps

1. **Install `react-markdown`** for Web UI:
   ```bash
   cd /root/qwen/base/it-lead-mcp-server/web-ui/frontend
   npm install react-markdown
   ```

2. **Add file preview dialog** to TaskManagement.jsx

3. **Add API endpoint** to serve file content

4. **Test end-to-end** with PDF upload

## Files Modified

1. `/root/qwen/base/it-lead-mcp-server/web-ui/backend/git_result_storage.py`
   - Added `clean_llm_response()` function
   - Added `combine_pages_to_markdown()` function
   - Updated `store_document_result()` to clean content before saving

## Files Pending

1. `/root/qwen/base/it-lead-mcp-server/web-ui/frontend/src/components/TaskManagement.jsx`
   - Add file preview dialog
   - Make files clickable
   - Add file type filters

2. `/root/qwen/base/it-lead-mcp-server/web-ui/backend/main.py`
   - Add file content endpoint
