"""
Theme Color Migration Script
Replaces Tailwind hardcoded colors with theme-aware classes.
Local Insight v1.9.0
"""

import os
import re

# Replacement mapping
REPLACEMENTS = {
    # Background colors
    'bg-gray-950': 'bg-theme-base',
    'bg-gray-900': 'bg-theme-surface',
    'bg-gray-800': 'bg-theme-elevated',
    'bg-gray-700': 'bg-theme-hover',
    'bg-gray-600': 'bg-theme-active',
    
    # Background with opacity (partial replacement)
    'bg-gray-800/50': 'bg-theme-elevated/50',
    'bg-gray-900/50': 'bg-theme-surface/50',
    'bg-gray-800/80': 'bg-theme-elevated/80',
    'bg-gray-900/80': 'bg-theme-surface/80',
    'bg-gray-800/90': 'bg-theme-elevated/90',
    'bg-gray-900/90': 'bg-theme-surface/90',
    
    # Hover backgrounds
    'hover:bg-gray-700': 'hover:bg-theme-hover',
    'hover:bg-gray-800': 'hover:bg-theme-elevated',
    'hover:bg-gray-600': 'hover:bg-theme-active',
    
    # Border colors
    'border-gray-700': 'border-theme-default',
    'border-gray-800': 'border-theme-subtle',
    'border-gray-600': 'border-theme-hover',
    
    # Hover borders
    'hover:border-gray-600': 'hover:border-theme-hover',
    'hover:border-gray-700': 'hover:border-theme-default',
    
    # Focus states for primary
    'focus:border-blue-500': 'focus:border-theme-primary',
    'focus:ring-blue-500': 'focus:ring-theme-primary',
    'focus:ring-purple-500': 'focus:ring-theme-accent',
    
    # Text colors
    'text-gray-100': 'text-theme-primary',
    'text-gray-200': 'text-theme-primary',
    'text-gray-300': 'text-theme-primary',
    'text-gray-400': 'text-theme-secondary',
    'text-gray-500': 'text-theme-muted',
    
    # Primary button colors (blue)
    'bg-blue-600': 'bg-theme-primary',
    'bg-blue-500': 'bg-theme-primary',
    'hover:bg-blue-500': 'hover:bg-theme-primary-hover',
    'hover:bg-blue-600': 'hover:bg-theme-primary-hover',
    'text-blue-400': 'text-theme-brand-light',
    'text-blue-500': 'text-theme-brand',
    'border-blue-500': 'border-theme-primary',
    
    # Accent colors (purple)
    'bg-purple-600': 'bg-theme-accent',
    'bg-purple-500': 'bg-theme-accent',
    'hover:bg-purple-500': 'hover:bg-theme-accent-hover',
    'hover:bg-purple-600': 'hover:bg-theme-accent-hover',
    'text-purple-400': 'text-theme-accent-light',
    'text-purple-500': 'text-theme-accent',
    
    # Gradients - use CSS classes
    'from-blue-400 to-purple-400': 'brand-gradient-text', 
    
    # Placeholder text
    'placeholder-gray-500': 'placeholder-theme-muted',
    'placeholder-gray-400': 'placeholder-theme-secondary',
    
    # Ring colors
    'ring-blue-500': 'ring-theme-primary',
    'ring-gray-700': 'ring-theme-default',
    
    # Divide colors
    'divide-gray-700': 'divide-theme-default',
    'divide-gray-800': 'divide-theme-subtle',
}

# Files to process
TEMPLATE_DIRS = [
    r'c:\AI\Local Insight\templates\components',
    r'c:\AI\Local Insight\templates\prompt-builder',
]

def replace_in_file(filepath):
    """Replace all occurrences in a file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    changes = 0
    
    for old, new in REPLACEMENTS.items():
        if old in content:
            count = content.count(old)
            content = content.replace(old, new)
            changes += count
            print(f"  {old} -> {new} ({count})")
    
    if changes > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return changes
    return 0

def main():
    total_changes = 0
    processed_files = 0
    
    for dir_path in TEMPLATE_DIRS:
        if not os.path.exists(dir_path):
            print(f"Directory not found: {dir_path}")
            continue
            
        for filename in os.listdir(dir_path):
            if filename.endswith('.html'):
                filepath = os.path.join(dir_path, filename)
                print(f"\nProcessing: {filename}")
                changes = replace_in_file(filepath)
                if changes > 0:
                    total_changes += changes
                    processed_files += 1
                    print(f"  Total changes: {changes}")
                else:
                    print("  No changes needed")
    
    print(f"\n=== Summary ===")
    print(f"Files modified: {processed_files}")
    print(f"Total replacements: {total_changes}")

if __name__ == '__main__':
    main()
