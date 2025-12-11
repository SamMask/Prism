# Check if Array.isArray exists in index.html
with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.split('\n')
    
    for i, line in enumerate(lines, 1):
        if 'Array.isArray' in line:
            print(f"Line {i}: {line.strip()[:80]}")
    
    if 'Array.isArray' not in content:
        print("NOT FOUND: Array.isArray is not in the file!")
    else:
        print("\nFOUND: Array.isArray exists in the file.")
