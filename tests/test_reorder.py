import pytest
import json

def test_reorder_api(client):
    """Test reorder API with created notes"""
    
    # 1. Create 3 notes
    note_ids = []
    for i in range(3):
        resp = client.post("/api/notes", json={
            "title": f"Note {i}",
            "content": "Content",
            "type": "Test"
        })
        assert resp.status_code == 201, f"Failed to create note: {resp.data}"
        data = resp.get_json()
        note_ids.append(data['data']['note_id'])
    
    print(f"Created notes: {note_ids}")
    
    # 2. Reorder them (reverse order)
    reversed_ids = list(reversed(note_ids))
    
    response = client.put(
        '/api/notes/reorder',
        json={'note_ids': reversed_ids}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(f"Error: {response.data}")
        
    assert response.status_code == 200
    
    result = response.get_json()
    assert result['status'] == 'success'
