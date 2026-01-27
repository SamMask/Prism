import os

file_path = r'garbage-can/007-Prism V1.4.2後的昇級方向.md'

if os.path.exists(file_path):
    print(f"\n<<<< START FILE: {os.path.basename(file_path)} >>>>")
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
            print(file.read())
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    print(f"<<<< END FILE: {os.path.basename(file_path)} >>>>\n")
else:
    print(f"File not found: {file_path}")
