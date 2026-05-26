import glob
import os

files = ['000.txt'] + glob.glob('garbage-can/007*.md') + glob.glob('garbage-can/006*.md')
print("Found files:", files)

for f in files:
    if os.path.exists(f):
        print(f"\n<<<< START {f} >>>>")
        try:
            with open(f, 'r', encoding='utf-8', errors='replace') as file:
                print(file.read())
        except Exception as e:
            print(f"Error: {e}")
        print(f"<<<< END {f} >>>>\n")
    else:
        print(f"File not found: {f}")
