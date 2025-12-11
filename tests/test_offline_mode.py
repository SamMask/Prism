"""
測試離線模式 - 驗證前端資源本地化
確認應用在無網路環境下能正常運作
"""

import os
import sys

def check_file_exists(filepath, description):
    """檢查檔案是否存在"""
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        size_kb = size / 1024
        print(f"  [OK] {description}: {filepath} ({size_kb:.1f} KB)")
        return True
    else:
        print(f"  [FAIL] {description} not found: {filepath}")
        return False


def main():
    print("=" * 70)
    print("Offline Mode Test - Frontend Resources Localization")
    print("=" * 70)

    print("\n[TEST 1] Checking local resource directories...")

    # 檢查目錄
    directories = [
        ('static/js', 'JavaScript directory'),
        ('static/css', 'CSS directory'),
        ('static/lib', 'Library directory')
    ]

    all_dirs_exist = True
    for dir_path, desc in directories:
        if os.path.isdir(dir_path):
            print(f"  [OK] {desc}: {dir_path}/")
        else:
            print(f"  [FAIL] {desc} not found: {dir_path}/")
            all_dirs_exist = False

    if not all_dirs_exist:
        print("\n[FAIL] Directory structure incomplete!")
        sys.exit(1)

    print("\n[TEST 2] Checking downloaded resources...")

    # 檢查檔案
    resources = [
        ('static/js/vue.global.js', 'Vue.js 3'),
        ('static/css/tailwind.js', 'Tailwind CSS'),
        ('static/lib/marked.min.js', 'Marked.js')
    ]

    all_files_exist = True
    for filepath, desc in resources:
        if not check_file_exists(filepath, desc):
            all_files_exist = False

    if not all_files_exist:
        print("\n[FAIL] Some resources are missing!")
        sys.exit(1)

    print("\n[TEST 3] Checking index.html references...")

    # 檢查 index.html 是否使用本地路徑
    with open('templates/index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    checks = [
        ('/static/js/vue.global.js', 'Vue.js local path'),
        ('/static/css/tailwind.js', 'Tailwind CSS local path'),
        ('/static/lib/marked.min.js', 'Marked.js local path')
    ]

    all_refs_correct = True
    for path, desc in checks:
        if path in content:
            print(f"  [OK] {desc} found in index.html")
        else:
            print(f"  [FAIL] {desc} NOT found in index.html")
            all_refs_correct = False

    # 檢查是否還有 CDN 引用
    cdn_patterns = [
        'cdn.tailwindcss.com',
        'unpkg.com',
        'cdn.jsdelivr.net'
    ]

    has_cdn = False
    for pattern in cdn_patterns:
        if pattern in content:
            print(f"  [WARN] CDN reference still exists: {pattern}")
            has_cdn = True

    if has_cdn:
        print("\n[WARN] Some CDN references still exist in index.html")
        print("        Please ensure all external resources are localized.")

    if not all_refs_correct:
        print("\n[FAIL] index.html references incomplete!")
        sys.exit(1)

    # 最終結果
    print("\n" + "=" * 70)
    if all_dirs_exist and all_files_exist and all_refs_correct and not has_cdn:
        print("[SUCCESS] All offline mode tests passed!")
        print("          The application can now run completely offline.")
        print("\n[NEXT STEP] Manual verification:")
        print("  1. Start the application: python app.py")
        print("  2. Disconnect from internet")
        print("  3. Visit http://localhost:5000")
        print("  4. Verify that the page loads correctly with all styles and functionality")
    else:
        print("[PARTIAL] Some tests passed, but issues were found.")
        print("          Please review the warnings above.")
    print("=" * 70)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INFO] Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
