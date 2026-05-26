"""
Test GROUP_CONCAT separator fix (Standard Pytest Version)
"""
import pytest

def test_comma_in_tags_flow(client):
    """Test full flow: Create -> Get Single -> Get List -> Delete"""
    
    # 1. Create Note
    print("\n[TEST 1] Creating note with comma in tags...")
    test_note = {
        "title": "Test Comma Separator Fix",
        "content": "# Test Content\n\nThis tests the GROUP_CONCAT separator fix.",
        "type": "Test",
        "remarks": "Test note",
        "tags": ["AI, ML", "Python, Flask", "Normal Tag"],
        "urls": [
            "https://example.com/ai,ml",
            "https://example.com/normal"
        ]
    }

    response = client.post("/api/notes", json=test_note)
    assert response.status_code == 201
    
    data = response.get_json()
    note_id = data['data']['note_id']
    print(f"[OK] Created successfully! Note ID: {note_id}")

    # 2. Get Single Note
    print(f"\n[TEST 2] Getting note ID {note_id}...")
    response = client.get(f"/api/notes/{note_id}")
    assert response.status_code == 200
    
    note = response.get_json()['data']
    print(f"Tags: {note['tags']}")
    
    # Extract tag names (API returns [{id, name}, ...])
    actual_tags = [t['name'] if isinstance(t, dict) else t for t in note['tags']]
    expected_tags = ["AI, ML", "Python, Flask", "Normal Tag"]
    
    assert sorted(actual_tags) == sorted(expected_tags), \
        f"Expected {expected_tags}, got {actual_tags}"
    print("[OK] Tags parsed correctly!")

    # 3. Get All Notes
    print(f"\n[TEST 3] Getting all notes...")
    response = client.get("/api/notes")
    assert response.status_code == 200
    
    notes = response.get_json()['data']
    # Find our test note
    found_note = next((n for n in notes if n['id'] == note_id), None)
    assert found_note is not None
    
    # Extract tag names from list response
    list_tags = [t['name'] if isinstance(t, dict) else t for t in found_note['tags']]
    print(f"List Tags: {list_tags}")
    
    assert "AI, ML" in list_tags, f"Expected 'AI, ML' in {list_tags}"
    print("[OK] Tags parsed correctly in list query!")

    # 4. Cleanup
    print(f"\n[CLEANUP] Deleting test note ID {note_id}...")
    response = client.delete(f"/api/notes/{note_id}")
    assert response.status_code == 200
    print("[OK] Test note deleted")
