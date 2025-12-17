"""
Automated GROUP_CONCAT separator fix test (Pytest Conversion)
"""
import pytest

def test_comma_in_tags_auto(client):
    """Automated test for comma separator in tags using pytest client"""
    
    print("=" * 60)
    print("GROUP_CONCAT Separator Fix Test (Automated)")
    print("=" * 60)

    # Test 1: Create note
    print("\n[TEST 1] Creating note with comma in tags...")
    test_note = {
        "title": "Test Comma Separator Fix",
        "content": "# Test Content",
        "type": "Test",
        "tags": ["AI, ML", "Python, Flask", "Normal Tag"],
        "urls": ["https://example.com/ai,ml", "https://example.com/normal"]
    }

    response = client.post("/api/notes", json=test_note)
    assert response.status_code == 201, f"Creation failed: {response.data}"
    
    data = response.get_json()
    note_id = data['data']['note_id']
    print(f"[OK] Created successfully! Note ID: {note_id}")

    # Test 2: Get single note
    print(f"\n[TEST 2] Getting note ID {note_id}...")
    response = client.get(f"/api/notes/{note_id}")
    assert response.status_code == 200, f"Get failed: {response.data}"
    
    note = response.get_json()['data']
    expected_tags = ["AI, ML", "Python, Flask", "Normal Tag"]

    print(f"Title: {note['title']}")
    print(f"Tags: {note['tags']}")
    print(f"URLs: {note['urls']}")

    # Extract tag names (API returns [{id, name}, ...])
    actual_tags = [t['name'] if isinstance(t, dict) else t for t in note['tags']]
    assert sorted(actual_tags) == sorted(expected_tags), \
        f"Tags parsing error! Expected: {expected_tags}, Actual: {actual_tags}"
    print("[OK] Tags parsed correctly!")

    # Test 3: Get all notes
    print(f"\n[TEST 3] Getting all notes...")
    response = client.get("/api/notes")
    assert response.status_code == 200, f"Get failed: {response.data}"

    notes = response.get_json()['data']
    test_note = next((n for n in notes if n['id'] == note_id), None)
    
    assert test_note, "Test note not found in list"
    
    # Extract tag names
    list_tags = [t['name'] if isinstance(t, dict) else t for t in test_note['tags']]
    assert "AI, ML" in list_tags, f"Tags parsing error in list query: {list_tags}"

    print(f"[OK] Retrieved {len(notes)} notes, tags correct in list query!")

    # Cleanup
    print(f"\n[CLEANUP] Deleting test note ID {note_id}...")
    response = client.delete(f"/api/notes/{note_id}")
    assert response.status_code == 200, f"Deletion failed: {response.data}"
    print("[OK] Test note deleted")

    print("\n" + "=" * 60)
    print("[SUCCESS] All tests passed!")
    print("=" * 60)
