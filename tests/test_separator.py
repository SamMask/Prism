"""
測試 GROUP_CONCAT 分隔符修正
驗證標籤名稱包含逗號時不會被錯誤分割
"""

import requests
import json

# API 基礎 URL
BASE_URL = 'http://localhost:5000/api'


def test_create_note_with_comma_in_tag():
    """
    測試建立包含逗號的標籤
    例如: "AI, ML" 這個標籤名稱包含逗號，測試是否正確處理
    """
    print("\n【測試 1】建立包含逗號標籤的筆記...")

    test_note = {
        "title": "測試逗號分隔符修正",
        "content": "# 測試內容\n\n這是用來驗證 GROUP_CONCAT 分隔符修正的測試筆記。",
        "type": "測試",
        "remarks": "測試用筆記",
        "tags": ["AI, ML", "Python, Flask", "正常標籤"],  # 包含逗號的標籤
        "urls": [
            "https://example.com/ai,ml",  # 包含逗號的網址
            "https://example.com/normal"
        ]
    }

    response = requests.post(f"{BASE_URL}/notes", json=test_note)

    if response.status_code == 201:
        result = response.json()
        note_id = result['data']['note_id']
        print(f"✅ 建立成功! Note ID: {note_id}")
        return note_id
    else:
        print(f"❌ 建立失敗: {response.text}")
        return None


def test_get_note(note_id):
    """
    測試取得單一筆記，驗證標籤是否正確解析
    """
    print(f"\n【測試 2】取得筆記 ID {note_id}...")

    response = requests.get(f"{BASE_URL}/notes/{note_id}")

    if response.status_code == 200:
        result = response.json()
        note = result['data']

        print(f"📝 標題: {note['title']}")
        print(f"🏷️  標籤: {note['tags']}")
        print(f"🔗 網址: {note['urls']}")

        # 驗證標籤數量
        expected_tags = ["AI, ML", "Python, Flask", "正常標籤"]
        if note['tags'] == expected_tags:
            print("✅ 標籤解析正確！包含逗號的標籤沒有被錯誤分割。")
        else:
            print(f"❌ 標籤解析錯誤！")
            print(f"   預期: {expected_tags}")
            print(f"   實際: {note['tags']}")

        # 驗證網址數量
        expected_urls = ["https://example.com/ai,ml", "https://example.com/normal"]
        if note['urls'] == expected_urls:
            print("✅ 網址解析正確！包含逗號的網址沒有被錯誤分割。")
        else:
            print(f"❌ 網址解析錯誤！")
            print(f"   預期: {expected_urls}")
            print(f"   實際: {note['urls']}")

        return True
    else:
        print(f"❌ 取得失敗: {response.text}")
        return False


def test_get_all_notes():
    """
    測試取得所有筆記列表
    """
    print(f"\n【測試 3】取得所有筆記列表...")

    response = requests.get(f"{BASE_URL}/notes")

    if response.status_code == 200:
        result = response.json()
        notes = result['data']

        print(f"✅ 成功取得 {len(notes)} 則筆記")

        # 檢查測試筆記
        test_note = next((n for n in notes if n['type'] == '測試'), None)
        if test_note:
            print(f"🏷️  測試筆記標籤: {test_note['tags']}")
            if "AI, ML" in test_note['tags']:
                print("✅ 列表查詢中標籤也解析正確！")
            else:
                print("❌ 列表查詢中標籤解析錯誤！")

        return True
    else:
        print(f"❌ 取得失敗: {response.text}")
        return False


def cleanup(note_id):
    """
    清理測試資料
    """
    print(f"\n【清理】刪除測試筆記 ID {note_id}...")

    response = requests.delete(f"{BASE_URL}/notes/{note_id}")

    if response.status_code == 200:
        print("✅ 測試筆記已刪除")
    else:
        print(f"⚠️  刪除失敗（可能需要手動清理）: {response.text}")


if __name__ == '__main__':
    print("=" * 60)
    print("GROUP_CONCAT 分隔符修正測試")
    print("=" * 60)

    # 執行測試流程
    note_id = test_create_note_with_comma_in_tag()

    if note_id:
        test_get_note(note_id)
        test_get_all_notes()

        # 詢問是否清理測試資料
        cleanup_choice = input("\n是否刪除測試筆記? (y/n): ").strip().lower()
        if cleanup_choice == 'y':
            cleanup(note_id)
        else:
            print(f"ℹ️  保留測試筆記 (ID: {note_id})，請稍後手動刪除")

    print("\n" + "=" * 60)
    print("測試完成")
    print("=" * 60)
