import glob
import os

files = [
    r'garbage-can/006-V3可參考的github專案及用pywebview開啟.md',
    r'garbage-can/008-改良方案-但這好象就是我們目前的流程了.txt',
    r'garbage-can/997-1215-Prism_V2 個人特化版深度戰略架構與功能優化研究報告.md',
    r'garbage-can/998-福爾摩斯的偵探文件.txt'
]

print("Starting file dump...\n")
for f in files:
    if os.path.exists(f):
        print(f"\n<<<< START FILE: {os.path.basename(f)} >>>>")
        try:
            with open(f, 'r', encoding='utf-8', errors='replace') as file:
                print(file.read())
        except Exception as e:
            print(f"Error reading {f}: {e}")
        print(f"<<<< END FILE: {os.path.basename(f)} >>>>\n")
    else:
        print(f"File not found: {f}")
