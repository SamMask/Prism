"""
測試 API 分頁功能
建立 100+ 筆測試資料並驗證分頁正確性
"""

import requests
import json
import sys

BASE_URL = 'http://localhost:5000/api'


def create_test_notes(count=105):
    """建立測試筆記資料"""
    print(f"\n[SETUP] Creating {count} test notes...")

    created_ids = []

    for i in range(1, count + 1):
        note = {
            "title": f"Test Note {i:03d}",
            "content": f"# Test Content {i}\n\nThis is test note number {i}.",
            "type": "測試",
            "remarks": f"Test note {i}",
            "tags": [f"Tag{(i-1)%10+1}", "測試"],
            "urls": [f"https://example.com/note{i}"]
        }

        response = requests.post(f"{BASE_URL}/notes", json=note)

        if response.status_code == 201:
            note_id = response.json()['data']['note_id']
            created_ids.append(note_id)

            if i % 20 == 0:
                print(f"  Created {i}/{count} notes...")
        else:
            print(f"[ERROR] Failed to create note {i}: {response.text}")
            return []

    print(f"[OK] Successfully created {len(created_ids)} test notes")
    return created_ids


def test_default_pagination():
    """測試預設分頁參數"""
    print("\n[TEST 1] Testing default pagination...")

    response = requests.get(f"{BASE_URL}/notes")

    if response.status_code != 200:
        print(f"[FAIL] Request failed: {response.text}")
        return False

    result = response.json()

    # 驗證回應結構
    if 'pagination' not in result:
        print("[FAIL] Missing 'pagination' in response")
        return False

    pagination = result['pagination']

    # 驗證預設值
    if pagination['page'] != 1:
        print(f"[FAIL] Expected page=1, got {pagination['page']}")
        return False

    if pagination['per_page'] != 20:
        print(f"[FAIL] Expected per_page=20, got {pagination['per_page']}")
        return False

    if len(result['data']) > 20:
        print(f"[FAIL] Expected at most 20 notes, got {len(result['data'])}")
        return False

    print(f"[OK] Default pagination works correctly")
    print(f"     Page: {pagination['page']}, Per page: {pagination['per_page']}")
    print(f"     Total: {pagination['total']}, Total pages: {pagination['total_pages']}")
    print(f"     Notes returned: {len(result['data'])}")

    return True


def test_custom_pagination():
    """測試自定義分頁參數"""
    print("\n[TEST 2] Testing custom pagination (page=2, per_page=10)...")

    response = requests.get(f"{BASE_URL}/notes?page=2&per_page=10")

    if response.status_code != 200:
        print(f"[FAIL] Request failed: {response.text}")
        return False

    result = response.json()
    pagination = result['pagination']

    if pagination['page'] != 2:
        print(f"[FAIL] Expected page=2, got {pagination['page']}")
        return False

    if pagination['per_page'] != 10:
        print(f"[FAIL] Expected per_page=10, got {pagination['per_page']}")
        return False

    if len(result['data']) > 10:
        print(f"[FAIL] Expected at most 10 notes, got {len(result['data'])}")
        return False

    print(f"[OK] Custom pagination works correctly")
    print(f"     Notes returned: {len(result['data'])}")

    return True


def test_max_per_page():
    """測試 per_page 最大值限制"""
    print("\n[TEST 3] Testing max per_page limit (requesting 150, should cap at 100)...")

    response = requests.get(f"{BASE_URL}/notes?per_page=150")

    if response.status_code != 200:
        print(f"[FAIL] Request failed: {response.text}")
        return False

    result = response.json()
    pagination = result['pagination']

    if pagination['per_page'] != 100:
        print(f"[FAIL] Expected per_page capped at 100, got {pagination['per_page']}")
        return False

    print(f"[OK] Max per_page limit enforced correctly")

    return True


def test_invalid_page():
    """測試無效頁碼處理"""
    print("\n[TEST 4] Testing invalid page numbers...")

    # 測試 page=0（應該被修正為 1）
    response = requests.get(f"{BASE_URL}/notes?page=0")
    result = response.json()

    if result['pagination']['page'] != 1:
        print(f"[FAIL] Expected page=0 to be corrected to 1, got {result['pagination']['page']}")
        return False

    # 測試 page=-5（應該被修正為 1）
    response = requests.get(f"{BASE_URL}/notes?page=-5")
    result = response.json()

    if result['pagination']['page'] != 1:
        print(f"[FAIL] Expected page=-5 to be corrected to 1, got {result['pagination']['page']}")
        return False

    print(f"[OK] Invalid page numbers handled correctly")

    return True


def test_last_page():
    """測試最後一頁資料"""
    print("\n[TEST 5] Testing last page...")

    # 先取得總頁數
    response = requests.get(f"{BASE_URL}/notes")
    result = response.json()
    total_pages = result['pagination']['total_pages']
    total = result['pagination']['total']

    # 請求最後一頁
    response = requests.get(f"{BASE_URL}/notes?page={total_pages}&per_page=20")
    result = response.json()

    # 最後一頁的筆記數應該是 total % 20（如果能整除則是 20）
    expected_count = total % 20 if total % 20 != 0 else 20
    actual_count = len(result['data'])

    if actual_count != expected_count:
        print(f"[FAIL] Expected {expected_count} notes on last page, got {actual_count}")
        return False

    print(f"[OK] Last page contains correct number of notes ({actual_count})")

    return True


def test_beyond_last_page():
    """測試超出最後一頁"""
    print("\n[TEST 6] Testing page beyond last page...")

    # 先取得總頁數
    response = requests.get(f"{BASE_URL}/notes")
    result = response.json()
    total_pages = result['pagination']['total_pages']

    # 請求超出範圍的頁碼
    response = requests.get(f"{BASE_URL}/notes?page={total_pages + 10}")
    result = response.json()

    if len(result['data']) != 0:
        print(f"[FAIL] Expected 0 notes beyond last page, got {len(result['data'])}")
        return False

    print(f"[OK] Page beyond last page returns empty data")

    return True


def cleanup_test_notes(note_ids):
    """清理測試筆記"""
    print(f"\n[CLEANUP] Deleting {len(note_ids)} test notes...")

    success_count = 0
    for note_id in note_ids:
        response = requests.delete(f"{BASE_URL}/notes/{note_id}")
        if response.status_code == 200:
            success_count += 1

    print(f"[OK] Deleted {success_count}/{len(note_ids)} test notes")


def main():
    print("=" * 70)
    print("API Pagination Test")
    print("=" * 70)

    # 建立測試資料
    test_note_ids = create_test_notes(105)

    if not test_note_ids:
        print("\n[ERROR] Failed to create test notes. Aborting tests.")
        sys.exit(1)

    try:
        # 執行測試
        tests = [
            test_default_pagination,
            test_custom_pagination,
            test_max_per_page,
            test_invalid_page,
            test_last_page,
            test_beyond_last_page
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
            print("[SUCCESS] All pagination tests passed!")
        else:
            print(f"[FAIL] {failed} test(s) failed")

    finally:
        # 清理測試資料
        cleanup_choice = input("\nDelete test notes? (y/n): ").strip().lower()
        if cleanup_choice == 'y':
            cleanup_test_notes(test_note_ids)
        else:
            print(f"[INFO] Test notes kept (IDs: {test_note_ids[0]} to {test_note_ids[-1]})")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INFO] Test interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        sys.exit(1)
