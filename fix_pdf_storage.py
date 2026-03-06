with open('/root/qwen/base/it-lead-mcp-server/web-ui/backend/git_result_storage.py', 'r') as f:
    content = f.read()

# Add cleaning functions after imports
old_imports = '''from pathlib import Path
from typing import Dict, Any, Optional, List
import git
import json
from datetime import datetime'''

new_imports = '''from pathlib import Path
from typing import Dict, Any, Optional, List
import git
import json
from datetime import datetime
import re


def clean_llm_response(content: str) -> str:
    """
    Clean LLM response to extract pure Markdown content.
    
    Removes:
    - "Here's the markdown..." introductions
    - "```markdown" code blocks wrappers
    - "```" closing markers
    - Unnecessary whitespace
    - Non-Markdown artifacts
    
    Args:
        content: Raw LLM response
        
    Returns:
        Cleaned Markdown content
    """
    if not content:
        return content
    
    # Remove common LLM introductions
    intro_patterns = [
        r"^.*?(here'?s?|here is|this is|below is)\\s+(the|a|an)?\\s*(markdown|md|document|file).*?[:\\n]",
        r"^.*?(i'?ll?|i will|let me|sure|certainly)\\s+(create|write|generate|provide).*?[:\\n]",
        r"^sure!?\\s*[:\\n]?",
        r"^certainly!?\\s*[:\\n]?",
        r"^here you go[:\\n]?",
        r"^here'?s?\\s+(what|the|a)\\s*[:\\n]?",
    ]
    
    for pattern in intro_patterns:
        content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.MULTILINE)
    
    # Remove markdown code block wrappers
    content = re.sub(r'^```markdown\\s*\\n?', '', content, flags=re.MULTILINE)
    content = re.sub(r'^```md\\s*\\n?', '', content, flags=re.MULTILINE)
    content = re.sub(r'^```\\s*\\n?$', '', content, flags=re.MULTILINE)
    content = re.sub(r'\\n```\\s*$', '', content)
    
    # Remove "End of document" type markers
    content = re.sub(r'\\n?\\s*[-=]{3,}\\s*(end|eof|end of document|conclusion).*$', '', content, flags=re.IGNORECASE)
    
    # Normalize multiple blank lines to double newline
    content = re.sub(r'\\n{3,}', '\\n\\n', content)
    
    # Remove leading/trailing whitespace from each line
    lines = [line.rstrip() for line in content.split('\\n')]
    content = '\\n'.join(lines)
    
    # Remove leading/trailing whitespace from entire content
    content = content.strip()
    
    return content


def combine_pages_to_markdown(pages: List[Dict[str, Any]]) -> str:
    """
    Combine multiple PDF pages into a single Markdown document.
    
    Args:
        pages: List of page dicts with 'page_number' and 'content' keys
        
    Returns:
        Combined Markdown document with page separators
    """
    if not pages:
        return ""
    
    # Sort pages by page number
    sorted_pages = sorted(pages, key=lambda x: x.get('page_number', 0))
    
    # Combine pages with separators
    combined = []
    for i, page in enumerate(sorted_pages):
        page_content = page.get('content', '')
        page_num = page.get('page_number', i + 1)
        
        # Add page separator (except for first page)
        if i > 0:
            combined.append(f"\\n\\n---\\n\\n")
            combined.append(f"**Page {page_num}**\\n\\n")
        
        combined.append(page_content)
    
    return ''.join(combined)

'''

if old_imports in content:
    content = content.replace(old_imports, new_imports)
    print("✅ Added cleaning functions")
else:
    print("❌ Could not find imports to patch")

# Update store_document_result to clean content
old_store_doc = '''        # Write document
        doc_file = task_dir / f"result{ext}"
        doc_file.write_text(content)'''

new_store_doc = '''        # Clean LLM response and write document
        cleaned_content = clean_llm_response(content)
        doc_file = task_dir / f"result{ext}"
        doc_file.write_text(cleaned_content)'''

if old_store_doc in content:
    content = content.replace(old_store_doc, new_store_doc)
    print("✅ Updated store_document_result to clean content")
else:
    print("❌ Could not find store_document_result to patch")

with open('/root/qwen/base/it-lead-mcp-server/web-ui/backend/git_result_storage.py', 'w') as f:
    f.write(content)

print("✅ git_result_storage.py updated")
