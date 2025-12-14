"""
測試 Tags 過濾器功能
驗證後端 API 能正確返回標籤列表
"""

import json
import pytest

def test_get_tags(client):
    """測試 GET /api/tags 端點"""
    response = client.get('/api/tags')
    
    assert response.status_code == 200
    data = response.json
    
    # 驗證回應結構
    assert data['status'] == 'success'
    tags = data['data']
    assert isinstance(tags, list)
    
    # 驗證預設標籤存在 (Init DB 時會建立 'Welcome' 標籤)
    tag_names = [t['name'] for t in tags]
    assert 'Welcome' in tag_names
    
    # 驗證標籤屬性
    welcome_tag = next(t for t in tags if t['name'] == 'Welcome')
    assert 'id' in welcome_tag
    assert 'count' in welcome_tag
    assert welcome_tag['count'] >= 1  # 至少有一篇 Welcome note

def test_frontend_integration_mock(client):
    """
    前端整合測試說明
    
    此測試腳本主要驗證後端 API。
    前端整合 (Vue.js + API) 需透過手動驗證或 E2E 測試工具 (如 Playwright) 進行。
    
    手動驗證重點:
    1. 側邊欄是否顯示 'Welcome' 標籤
    2. 點擊標籤是否能過濾筆記列表
    """
    pass
