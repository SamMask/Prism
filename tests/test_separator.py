"""
測試 GROUP_CONCAT 分隔符修正 (Pytest Client Version)
驗證標籤名稱包含逗號時不會被錯誤分割
"""
import pytest

def test_comma_in_tags_flow_full(client):
    """
    完整流程測試: 建立 -> 取得單一 -> 取得列表 -> 刪除
    驗證包含逗號的標籤處理
    """
    print("=" * 60)
    print("GROUP_CONCAT 分隔符修正測試 (Pytest)")
    print("=" * 60)

    # 1. 建立筆記
    print("\n【測試 1】建立包含逗號標籤的筆記...")
    test_note = {
        "title": "測試逗號分隔符修正",
        "content": "# 測試內容\n\n這是用來驗證 GROUP_CONCAT 分隔符修正的測試筆記。",
        "type": "測試",
        "remarks": "測試用筆記",
        "tags": ["AI, ML", "Python, Flask", "正常標籤"],
        "urls": [
            "https://example.com/ai,ml",
            "https://example.com/normal"
        ]
    }

    response = client.post("/api/notes", json=test_note)
    assert response.status_code == 201, f"建立失敗: {response.data}"
    
    data = response.get_json()
    note_id = data['data']['note_id']
    print(f"✅ 建立成功! Note ID: {note_id}")

    # 2. 取得單一筆記
    print(f"\n【測試 2】取得筆記 ID {note_id}...")
    response = client.get(f"/api/notes/{note_id}")
    assert response.status_code == 200, f"取得失敗: {response.data}"
    
    note = response.get_json()['data']
    print(f"📝 標題: {note['title']}")
    print(f"🏷️  標籤: {note['tags']}")
    print(f"🔗 網址: {note['urls']}")

    # 提取標籤名稱 (API 回傳 [{id, name}, ...])
    actual_tags = [t['name'] if isinstance(t, dict) else t for t in note['tags']]
    expected_tags = ["AI, ML", "Python, Flask", "正常標籤"]
    
    assert sorted(actual_tags) == sorted(expected_tags), \
        f"標籤解析錯誤! 預期: {expected_tags}, 實際: {actual_tags}"
    print("✅ 標籤解析正確！包含逗號的標籤沒有被錯誤分割。")

    # 驗證網址數量
    expected_urls = ["https://example.com/ai,ml", "https://example.com/normal"]
    assert sorted(note['urls']) == sorted(expected_urls), \
        f"網址解析錯誤! 預期: {expected_urls}, 實際: {note['urls']}"
    print("✅ 網址解析正確！")

    # 3. 取得所有筆記列表
    print(f"\n【測試 3】取得所有筆記列表...")
    response = client.get("/api/notes")
    assert response.status_code == 200, f"取得列表失敗: {response.data}"
    
    notes = response.get_json()['data']
    print(f"✅ 成功取得 {len(notes)} 則筆記")

    # 檢查測試筆記
    found_note = next((n for n in notes if n['id'] == note_id), None)
    assert found_note is not None, "列表中找不到測試筆記"
    
    # 提取標籤名稱
    list_tags = [t['name'] if isinstance(t, dict) else t for t in found_note['tags']]
    print(f"🏷️  測試筆記標籤: {list_tags}")
    assert "AI, ML" in list_tags, f"列表查詢中標籤解析錯誤: {list_tags}"
    print("✅ 列表查詢中標籤也解析正確！")

    # 4. 清理
    print(f"\n【清理】刪除測試筆記 ID {note_id}...")
    response = client.delete(f"/api/notes/{note_id}")
    assert response.status_code == 200, f"刪除失敗: {response.data}"
    print("✅ 測試筆記已刪除")

    print("\n" + "=" * 60)
    print("測試完成")
    print("=" * 60)
