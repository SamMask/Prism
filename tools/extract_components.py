#!/usr/bin/env python3
"""
Extract Jinja2 components from index.html for modularization.
This script extracts specific HTML sections into separate component files.
"""
import os
import re

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
COMPONENTS_DIR = os.path.join(TEMPLATES_DIR, 'components')
# Use backup file for extraction
INDEX_PATH = os.path.join(TEMPLATES_DIR, 'index.html.backup')

# Ensure components directory exists
os.makedirs(COMPONENTS_DIR, exist_ok=True)

def extract_lines(start_line: int, end_line: int, output_file: str, comment: str = None):
    """Extract lines from index.html to a component file."""
    with open(INDEX_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Convert to 0-indexed
    extracted = lines[start_line - 1:end_line]
    
    output_path = os.path.join(COMPONENTS_DIR, output_file)
    with open(output_path, 'w', encoding='utf-8') as f:
        if comment:
            f.write(f"<!-- {comment} -->\n")
        f.writelines(extracted)
    
    print(f"Extracted lines {start_line}-{end_line} to {output_file} ({len(extracted)} lines)")
    return len(extracted)

def main():
    print(f"Reading from: {INDEX_PATH}")
    print(f"Output to: {COMPONENTS_DIR}")
    print("-" * 50)
    
    # Based on analysis of index.html.backup structure:
    # Editor Modal: lines 1182-2475
    # Settings Modal: lines 2477-3384 (ends with </div> closing settings)
    # Context Menus: lines 3386-3537 (Tag Context Menu + Tag Rename Modal + Tag Merge Modal)
    # Scripts: lines 3540-3541 (just the script tag)
    
    components = [
        (1182, 2475, '_editor-modal.html', 'Editor Modal Component (v1.8.9)'),
        (2477, 3384, '_settings-modal.html', 'Settings Modal Component (v1.8.9)'),
        (3386, 3537, '_context-menus.html', 'Context Menus Component (v1.8.9)'),
        (3540, 3541, '_scripts.html', 'Scripts Component (v1.8.9)'),
    ]
    
    total_lines = 0
    for start, end, filename, comment in components:
        lines_extracted = extract_lines(start, end, filename, comment)
        total_lines += lines_extracted
    
    print("-" * 50)
    print(f"Total extracted: {total_lines} lines into {len(components)} components")

if __name__ == '__main__':
    main()
