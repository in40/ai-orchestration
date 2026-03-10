# PDF to Markdown Conversion Fixes

## Issues Identified

### 1. Non-Markdown LLM Responses Stored
**Problem**: Files contain raw LLM responses that are not properly formatted as Markdown.

**Solution**: Add content cleaning and Markdown formatting before storage.

### 2. Each Page Stored as Separate Block
**Problem**: Multi-page PDFs are converted to multiple separate Markdown blocks instead of one combined document.

**Solution**: Combine all pages into a single Markdown document with page separators.

### 3. Files Stored as .txt Instead of .md
**Problem**: Document results are stored with `.txt` extension instead of `.md`.

**Solution**: 
- Update `git_result_storage.py` to use `.md` extension for Markdown content
- Update Web UI file filter to include `.md` files

### 4. No Markdown Preview
**Problem**: `.md`/`.txt` files are not clickable to preview content.

**Solution**: Add clickable file links with Markdown preview dialog in Web UI.

## Files to Modify

1. `/root/qwen/base/it-lead-mcp-server/web-ui/backend/git_result_storage.py`
   - Change document extension from `.txt` to `.md` for Markdown content
   - Add content cleaning for LLM responses

2. `/root/qwen/base/it-lead-mcp-server/web-ui/backend/result_router.py`
   - Add Markdown formatting/cleaning before storage

3. `/root/qwen/base/it-lead-mcp-server/web-ui/frontend/src/components/TaskManagement.jsx`
   - Add file preview dialog
   - Make file links clickable
   - Update file filter to include `.md`

4. `/root/qwen/base/it-lead-mcp-server/web-ui/backend/main.py`
   - Add endpoint to serve file content for preview

## Implementation Plan

### Phase 1: Backend Storage Fixes
1. Update `store_document_result()` to use `.md` extension
2. Add content cleaning function to remove non-Markdown artifacts
3. Combine multiple pages into single document

### Phase 2: Web UI Display
1. Add file preview dialog component
2. Make file names clickable
3. Add API endpoint to serve file content
4. Update file type filters

### Phase 3: Testing
1. Test with PDF upload
2. Verify Markdown conversion
3. Verify file preview works
4. Verify `.md` files are properly filtered and displayed
