#!/usr/bin/env python3
"""Script to extract editor modal component from index.html"""
import sys

def main():
    source_file = r'c:\AI\Local Insight\templates\index.html'
    target_file = r'c:\AI\Local Insight\templates\components\_editor-modal.html'
    
    # Lines 1182-2475 (1-indexed) = indices 1181-2474 (0-indexed)
    start_line = 1181
    end_line = 2475
    
    with open(source_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Extract the lines
    extracted = lines[start_line:end_line]
    
    with open(target_file, 'w', encoding='utf-8') as f:
        f.writelines(extracted)
    
    print(f"Extracted {len(extracted)} lines to {target_file}")

if __name__ == '__main__':
    main()
