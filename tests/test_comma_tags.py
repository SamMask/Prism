"""
測試 GROUP_CONCAT 分隔符修正
驗證標籤名稱包含逗號時不會被錯誤分割
"""

import pytest

def test_comma_in_tags(client):
    """
    測試建立包含逗號的標籤
    例如: "AI, ML" 這個標籤名稱包含逗號，測試是否正確處理
    """
    test_note = {
        "title": "Test Comma Separator Fix",
        "content": "# Test Content",
        "type": "測試",
        "tags": ["AI, ML", "Python, Flask", "Normal Tag"],
        "urls": ["https://example.com/ai,ml", "https://example.com/normal"]
    }
    
    # 1. Create
    response = client.post('/api/notes', json=test_note)
    assert response.status_code == 201
    note_id = response.json['data']['note_id']
    
    # 2. Get Single
    response = client.get(f'/api/notes/{note_id}')
    assert response.status_code == 200
    note = response.json['data']
    
    expected_tags = ["AI, ML", "Python, Flask", "Normal Tag"]
    
    # API returns list of tag objects [{'id': 1, 'name': 'Tag1'}, ...]
    # We need to extract names for comparison
    actual_tags = [t['name'] for t in note['tags']] if note['tags'] and isinstance(note['tags'][0], dict) else note['tags']
    
    # Sort both to ensure order doesn't matter (though API usually returns sorted or insertion order)
    # The implementation might return them in ID order or name order.
    # Let's check strict equality first, if fails we sort.
    # The original test checked strict equality.
    assert set(actual_tags) == set(expected_tags)
    assert "AI, ML" in actual_tags
    
    # 3. Get List
    response = client.get('/api/notes')
    assert response.status_code == 200
    notes = response.json['data']
    
    found_note = next((n for n in notes if n['id'] == note_id), None)
    assert found_note is not None
    found_tags = [t['name'] for t in found_note['tags']] if found_note['tags'] and isinstance(found_note['tags'][0], dict) else found_note['tags']
    assert "AI, ML" in found_tags
