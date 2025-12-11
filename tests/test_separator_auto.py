"""
Automated GROUP_CONCAT separator fix test
"""

import requests
import sys

BASE_URL = 'http://localhost:5000/api'


def main():
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

    response = requests.post(f"{BASE_URL}/notes", json=test_note)
    if response.status_code != 201:
        print(f"[FAIL] Creation failed: {response.text}")
        sys.exit(1)

    note_id = response.json()['data']['note_id']
    print(f"[OK] Created successfully! Note ID: {note_id}")

    # Test 2: Get single note
    print(f"\n[TEST 2] Getting note ID {note_id}...")
    response = requests.get(f"{BASE_URL}/notes/{note_id}")
    if response.status_code != 200:
        print(f"[FAIL] Get failed: {response.text}")
        cleanup(note_id)
        sys.exit(1)

    note = response.json()['data']
    expected_tags = ["AI, ML", "Python, Flask", "Normal Tag"]

    print(f"Title: {note['title']}")
    print(f"Tags: {note['tags']}")
    print(f"URLs: {note['urls']}")

    if note['tags'] != expected_tags:
        print(f"[FAIL] Tags parsing error!")
        print(f"  Expected: {expected_tags}")
        print(f"  Actual: {note['tags']}")
        cleanup(note_id)
        sys.exit(1)

    print("[OK] Tags parsed correctly!")

    # Test 3: Get all notes
    print(f"\n[TEST 3] Getting all notes...")
    response = requests.get(f"{BASE_URL}/notes")
    if response.status_code != 200:
        print(f"[FAIL] Get failed: {response.text}")
        cleanup(note_id)
        sys.exit(1)

    notes = response.json()['data']
    test_note = next((n for n in notes if n['type'] == 'Test'), None)

    if not test_note or "AI, ML" not in test_note['tags']:
        print("[FAIL] Tags parsing error in list query!")
        cleanup(note_id)
        sys.exit(1)

    print(f"[OK] Retrieved {len(notes)} notes, tags correct in list query!")

    # Cleanup
    cleanup(note_id)

    print("\n" + "=" * 60)
    print("[SUCCESS] All tests passed!")
    print("=" * 60)


def cleanup(note_id):
    print(f"\n[CLEANUP] Deleting test note ID {note_id}...")
    response = requests.delete(f"{BASE_URL}/notes/{note_id}")
    if response.status_code == 200:
        print("[OK] Test note deleted")
    else:
        print(f"[WARN] Deletion failed: {response.text}")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        sys.exit(1)
