# Truncate index.html to remove orphan JavaScript code
# Keep only lines 1-2409 (HTML + ES Module import)

import os

input_file = 'templates/index.html'
output_file = 'templates/index_new.html'

print(f"Reading {input_file}...")
with open(input_file, 'r', encoding='utf-8') as f:
    all_lines = f.readlines()

print(f"Original file has {len(all_lines)} lines")

# Keep only first 2409 lines
clean_lines = all_lines[:2409]
print(f"Keeping {len(clean_lines)} lines")

# Write to new file first
with open(output_file, 'w', encoding='utf-8') as f:
    f.writelines(clean_lines)
print(f"Wrote {output_file}")

# Verify
with open(output_file, 'r', encoding='utf-8') as f:
    verify_lines = f.readlines()
print(f"Verified: {len(verify_lines)} lines")

# Replace original
os.replace(output_file, input_file)
print(f"Replaced {input_file} successfully!")

# Final verify
with open(input_file, 'r', encoding='utf-8') as f:
    final_lines = f.readlines()
print(f"Final: {len(final_lines)} lines")
