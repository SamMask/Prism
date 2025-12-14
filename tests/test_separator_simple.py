"""
Test GROUP_CONCAT separator fix (Windows-compatible version)
"""

import requests
import json

BASE_URL = 'http://localhost:5000/api'


def test_comma_in_tags():
    """Test creating note with comma in tag names"""
    print("\n[TEST 1] Creating note with comma in tags...")

    test_note = {
        "title": "Test Comma Separator Fix",
        "content": "# Test Content\n\nThis tests the GROUP_CONCAT separator fix.",
        "type": "Test",
        "remarks": "Test note",
        "tags": ["AI, ML", "Python, Flask", "Normal Tag"],  # Tags with commas
        "urls": [
            "https://example.com/ai,ml",  # URL with comma
            "https://example.com/normal"
        ]
    }

    response = requests.post(f"{BASE_URL}/notes", json=test_note)

    if response.status_code == 201:
        result = response.json()
        note_id = result['data']['note_id']
        print(f"[OK] Created successfully! Note ID: {note_id}")
        return note_id
    else:
        print(f"[FAIL] Creation failed: {response.text}")
        return None


def test_get_single_note(note_id):
    """Test getting single note"""
    print(f"\n[TEST 2] Getting note ID {note_id}...")

    response = requests.get(f"{BASE_URL}/notes/{note_id}")

    if response.status_code == 200:
        result = response.json()
        note = result['data']

        print(f"Title: {note['title']}")
        print(f"Tags: {note['tags']}")
        print(f"URLs: {note['urls']}")

        # Verify tags
        expected_tags = ["AI, ML", "Python, Flask", "Normal Tag"]
        if note['tags'] == expected_tags:
            print("[OK] Tags parsed correctly! Commas in tag names are preserved.")
            return True
        else:
            print(f"[FAIL] Tags parsing error!")
            print(f"  Expected: {expected_tags}")
            print(f"  Actual: {note['tags']}")
            return False
    else:
        print(f"[FAIL] Get failed: {response.text}")
        return False


def test_get_all_notes():
    """Test getting all notes"""
    print(f"\n[TEST 3] Getting all notes...")

    response = requests.get(f"{BASE_URL}/notes")

    if response.status_code == 200:
        result = response.json()
        notes = result['data']

        print(f"[OK] Retrieved {len(notes)} notes")

        # Find test note
        test_note = next((n for n in notes if n['type'] == 'Test'), None)
        if test_note:
            print(f"Test note tags: {test_note['tags']}")
            if "AI, ML" in test_note['tags']:
                print("[OK] Tags also parsed correctly in list query!")
                return True
            else:
                print("[FAIL] Tags parsing error in list query!")
                return False
        return True
    else:
        print(f"[FAIL] Get failed: {response.text}")
        return False


def cleanup(note_id):
    """Delete test note"""
    print(f"\n[CLEANUP] Deleting test note ID {note_id}...")

    response = requests.delete(f"{BASE_URL}/notes/{note_id}")

    if response.status_code == 200:
        print("[OK] Test note deleted")
    else:
        print(f"[WARN] Deletion failed (may need manual cleanup): {response.text}")


if __name__ == '__main__':
    print("=" * 60)
    print("GROUP_CONCAT Separator Fix Test")
    print("=" * 60)

    note_id = test_comma_in_tags()

    if note_id:
        success1 = test_get_single_note(note_id)
        success2 = test_get_all_notes()

        cleanup_choice = input("\nDelete test note? (y/n): ").strip().lower()
        if cleanup_choice == 'y':
            cleanup(note_id)
        else:
            print(f"[INFO] Test note kept (ID: {note_id}), please delete manually later")

        if success1 and success2:
            print("\n" + "=" * 60)
            print("[SUCCESS] All tests passed!")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("[FAIL] Some tests failed")
            print("=" * 60)
    else:
        print("\n[FAIL] Test aborted due to creation failure")
