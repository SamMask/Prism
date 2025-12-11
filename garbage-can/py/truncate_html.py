# Truncate index.html to first 2409 lines
with open('templates/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Keep only the first 2409 lines (HTML + ES Module import)
clean_lines = lines[:2409]

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.writelines(clean_lines)

print(f"Done! Truncated from {len(lines)} to {len(clean_lines)} lines")
