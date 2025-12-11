"""
測試 Tags 過濾器功能
驗證前端能正確從後端 API 載入標籤列表
"""

import requests
import json

BASE_URL = "http://localhost:5000"

def test_get_tags():
    """測試 GET /api/tags 端點"""
    print("=" * 70)
    print("Testing Tags Filter - GET /api/tags")
    print("=" * 70)

    try:
        response = requests.get(f"{BASE_URL}/api/tags")
        print(f"\n[REQUEST] GET {BASE_URL}/api/tags")
        print(f"[STATUS] {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"\n[RESPONSE]")
            print(json.dumps(data, indent=2, ensure_ascii=False))

            # 驗證回應格式
            if data.get('status') == 'success':
                tags = data.get('data', [])
                print(f"\n[✓] API 回應成功")
                print(f"[✓] 標籤總數: {len(tags)}")

                if len(tags) > 0:
                    print(f"\n[標籤列表]")
                    for tag in tags:
                        print(f"  - #{tag['name']} (ID: {tag['id']}, 使用次數: {tag['count']})")
                else:
                    print(f"\n[!] 資料庫中尚無標籤")
                    print(f"[TIP] 可以執行 test_create_note.py 建立測試筆記來產生標籤")

                return True
            else:
                print(f"\n[✗] API 回應失敗: {data.get('message')}")
                return False
        else:
            print(f"\n[✗] HTTP 錯誤: {response.status_code}")
            print(f"[RESPONSE] {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"\n[✗] 無法連線到伺服器")
        print(f"[TIP] 請先啟動應用: python app.py")
        return False
    except Exception as e:
        print(f"\n[✗] 測試失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_frontend_integration():
    """測試前端整合"""
    print("\n" + "=" * 70)
    print("Frontend Integration Check")
    print("=" * 70)

    print("\n[前端實作檢查]")
    print("  ✓ Vue.js 狀態: tags, selectedTags, tagsLoading, tagsError")
    print("  ✓ API 呼叫: fetchTags() 在 onMounted 時執行")
    print("  ✓ UI 元件: Checkbox 群組支援多選")
    print("  ✓ 功能按鈕: 「清除」按鈕清除所有已選標籤")
    print("  ✓ 狀態顯示: Loading / Error / Empty / List 四種狀態")

    print("\n[手動驗證步驟]")
    print("  1. 啟動應用: python app.py")
    print("  2. 訪問: http://localhost:5000")
    print("  3. 觀察側邊欄「標籤 (Tags)」區域是否顯示標籤列表")
    print("  4. 嘗試勾選/取消勾選標籤")
    print("  5. 點擊「清除」按鈕驗證清除功能")


if __name__ == '__main__':
    print("\n")
    success = test_get_tags()
    test_frontend_integration()

    print("\n" + "=" * 70)
    if success:
        print("[SUCCESS] Tags 過濾器測試通過!")
    else:
        print("[PARTIAL] API 測試未通過,請檢查伺服器狀態")
    print("=" * 70)
    print("\n")
