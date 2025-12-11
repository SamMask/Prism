"""
測試檔案上傳安全性 - Magic Numbers 檢查
驗證系統能夠正確阻止偽裝的惡意檔案
"""

import requests
import os
import sys

BASE_URL = 'http://localhost:5000/api'
TEST_FILES_DIR = 'test_files'


def create_test_files():
    """建立測試檔案"""
    print("\n[SETUP] Creating test files...")

    # 建立測試檔案目錄
    os.makedirs(TEST_FILES_DIR, exist_ok=True)

    # 1. 建立正常的 PNG 圖片檔案（簡單的 1x1 像素圖片）
    png_data = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG 檔案標頭
        0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
        0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
        0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4,
        0x89, 0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41,
        0x54, 0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00,
        0x05, 0x00, 0x01, 0x0D, 0x0A, 0x2D, 0xB4, 0x00,
        0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,
        0x42, 0x60, 0x82
    ])

    with open(os.path.join(TEST_FILES_DIR, 'valid_image.png'), 'wb') as f:
        f.write(png_data)
    print("  Created valid_image.png (real PNG file)")

    # 2. 建立正常的 JPEG 圖片檔案（最小的 JPEG）
    jpeg_data = bytes([
        0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46,  # JPEG 檔案標頭
        0x49, 0x46, 0x00, 0x01, 0x01, 0x00, 0x00, 0x01,
        0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
        0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08,
        0x07, 0x07, 0x07, 0x09, 0x09, 0x08, 0x0A, 0x0C,
        0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
        0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D,
        0x1A, 0x1C, 0x1C, 0x20, 0x24, 0x2E, 0x27, 0x20,
        0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
        0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27,
        0x39, 0x3D, 0x38, 0x32, 0x3C, 0x2E, 0x33, 0x34,
        0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
        0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4,
        0x00, 0x14, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x03, 0xFF, 0xC4, 0x00, 0x14,
        0x10, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01,
        0x00, 0x00, 0x3F, 0x00, 0x7F, 0xC0, 0x00, 0xFF,
        0xD9  # JPEG 結尾標記
    ])

    with open(os.path.join(TEST_FILES_DIR, 'valid_image.jpg'), 'wb') as f:
        f.write(jpeg_data)
    print("  Created valid_image.jpg (real JPEG file)")

    # 3. 建立偽裝的 EXE 檔案（Windows 可執行檔標頭）
    # MZ 標頭是 Windows PE 檔案的特徵
    exe_data = bytes([
        0x4D, 0x5A, 0x90, 0x00, 0x03, 0x00, 0x00, 0x00,  # MZ 標頭 (EXE 檔案)
        0x04, 0x00, 0x00, 0x00, 0xFF, 0xFF, 0x00, 0x00,
        0xB8, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
    ])
    exe_data += b'\x00' * 200  # 填充一些資料

    with open(os.path.join(TEST_FILES_DIR, 'malicious.jpg'), 'wb') as f:
        f.write(exe_data)
    print("  Created malicious.jpg (EXE file disguised as JPG)")

    # 4. 建立偽裝的 HTML 檔案
    html_data = b'<!DOCTYPE html><html><head><script>alert("XSS")</script></head></html>'

    with open(os.path.join(TEST_FILES_DIR, 'malicious.png'), 'wb') as f:
        f.write(html_data)
    print("  Created malicious.png (HTML file disguised as PNG)")

    # 5. 建立偽裝的文字檔案
    txt_data = b'This is a plain text file, not an image!'

    with open(os.path.join(TEST_FILES_DIR, 'fake_image.gif'), 'wb') as f:
        f.write(txt_data)
    print("  Created fake_image.gif (Text file disguised as GIF)")

    print("[OK] All test files created")


def test_upload_valid_image():
    """測試上傳正常圖片（應該成功）"""
    print("\n[TEST 1] Uploading valid PNG image...")

    filepath = os.path.join(TEST_FILES_DIR, 'valid_image.png')

    with open(filepath, 'rb') as f:
        files = {'file': ('test.png', f, 'image/png')}
        response = requests.post(f"{BASE_URL}/upload", files=files)

    if response.status_code == 201:
        result = response.json()
        print(f"[OK] Valid image accepted: {result['data']['url']}")
        return True
    else:
        print(f"[FAIL] Valid image rejected: {response.text}")
        return False


def test_upload_valid_jpeg():
    """測試上傳正常 JPEG 圖片（應該成功）"""
    print("\n[TEST 2] Uploading valid JPEG image...")

    filepath = os.path.join(TEST_FILES_DIR, 'valid_image.jpg')

    with open(filepath, 'rb') as f:
        files = {'file': ('test.jpg', f, 'image/jpeg')}
        response = requests.post(f"{BASE_URL}/upload", files=files)

    if response.status_code == 201:
        result = response.json()
        print(f"[OK] Valid JPEG accepted: {result['data']['url']}")
        return True
    else:
        print(f"[FAIL] Valid JPEG rejected: {response.text}")
        return False


def test_upload_exe_disguised_as_jpg():
    """測試上傳偽裝成 JPG 的 EXE 檔案（應該被拒絕）"""
    print("\n[TEST 3] Uploading EXE file disguised as JPG...")

    filepath = os.path.join(TEST_FILES_DIR, 'malicious.jpg')

    with open(filepath, 'rb') as f:
        files = {'file': ('malicious.jpg', f, 'image/jpeg')}
        response = requests.post(f"{BASE_URL}/upload", files=files)

    if response.status_code == 400:
        result = response.json()
        print(f"[OK] Malicious file rejected: {result['message']}")
        return True
    else:
        print(f"[FAIL] Malicious file was accepted! This is a security vulnerability!")
        print(f"       Response: {response.text}")
        return False


def test_upload_html_disguised_as_png():
    """測試上傳偽裝成 PNG 的 HTML 檔案（應該被拒絕）"""
    print("\n[TEST 4] Uploading HTML file disguised as PNG...")

    filepath = os.path.join(TEST_FILES_DIR, 'malicious.png')

    with open(filepath, 'rb') as f:
        files = {'file': ('malicious.png', f, 'image/png')}
        response = requests.post(f"{BASE_URL}/upload", files=files)

    if response.status_code == 400:
        result = response.json()
        print(f"[OK] Malicious file rejected: {result['message']}")
        return True
    else:
        print(f"[FAIL] Malicious file was accepted! This is a security vulnerability!")
        return False


def test_upload_text_disguised_as_gif():
    """測試上傳偽裝成 GIF 的文字檔案（應該被拒絕）"""
    print("\n[TEST 5] Uploading text file disguised as GIF...")

    filepath = os.path.join(TEST_FILES_DIR, 'fake_image.gif')

    with open(filepath, 'rb') as f:
        files = {'file': ('fake.gif', f, 'image/gif')}
        response = requests.post(f"{BASE_URL}/upload", files=files)

    if response.status_code == 400:
        result = response.json()
        print(f"[OK] Fake file rejected: {result['message']}")
        return True
    else:
        print(f"[FAIL] Fake file was accepted!")
        return False


def cleanup_test_files():
    """清理測試檔案"""
    print("\n[CLEANUP] Removing test files...")

    try:
        for filename in os.listdir(TEST_FILES_DIR):
            filepath = os.path.join(TEST_FILES_DIR, filename)
            os.remove(filepath)
        os.rmdir(TEST_FILES_DIR)
        print("[OK] Test files removed")
    except Exception as e:
        print(f"[WARN] Cleanup failed: {e}")


def main():
    print("=" * 70)
    print("File Upload Security Test - Magic Numbers Validation")
    print("=" * 70)

    # 建立測試檔案
    create_test_files()

    try:
        # 執行測試
        tests = [
            test_upload_valid_image,
            test_upload_valid_jpeg,
            test_upload_exe_disguised_as_jpg,
            test_upload_html_disguised_as_png,
            test_upload_text_disguised_as_gif
        ]

        passed = 0
        failed = 0

        for test_func in tests:
            if test_func():
                passed += 1
            else:
                failed += 1

        # 輸出結果
        print("\n" + "=" * 70)
        print(f"Test Results: {passed} passed, {failed} failed")
        print("=" * 70)

        if failed == 0:
            print("[SUCCESS] All security tests passed!")
            print("          The system successfully blocks malicious files.")
        else:
            print(f"[FAIL] {failed} test(s) failed")
            print("       Security vulnerability detected!")

    finally:
        # 清理測試檔案
        cleanup_choice = input("\nDelete test files? (y/n): ").strip().lower()
        if cleanup_choice == 'y':
            cleanup_test_files()
        else:
            print(f"[INFO] Test files kept in {TEST_FILES_DIR}/ directory")


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
