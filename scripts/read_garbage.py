import os
import glob

# Search for the files
files = glob.glob('garbage-can/007*.md') + glob.glob('garbage-can/006*.md')
for f in files:
    print(f"--- START {f} ---")
    try:
        with open(f, 'r', encoding='utf-8') as file:
            print(file.read())
    except Exception as e:
        print(f"Error reading {f}: {e}")
    print(f"--- END {f} ---")
