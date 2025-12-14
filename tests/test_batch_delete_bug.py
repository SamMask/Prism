
import pytest
import sqlite3
import json

def test_batch_delete_notes(client, app):
    """
    Test case for verifying the fix of the batch delete bug.
    Specifically tests that multiple notes can be deleted without causing a TypeError
    in _cleanup_note_images.
    """
    
    # 1. Create a few notes with unique titles
    with app.app_context():
        db = sqlite3.connect(app.config['DATABASE'])
        db.execute("INSERT INTO Notes (title, content, type) VALUES ('BatchDeleteTest1', 'Content 1', '筆記')")
        db.execute("INSERT INTO Notes (title, content, type) VALUES ('BatchDeleteTest2', 'Content 2', '筆記')")
        db.execute("INSERT INTO Notes (title, content, type) VALUES ('BatchDeleteTest3', 'Content 3', '筆記')")
        db.commit()
        
        # Get only the test notes IDs (not the welcome note)
        notes = db.execute("SELECT id FROM Notes WHERE title LIKE 'BatchDeleteTest%'").fetchall()
        note_ids = [n[0] for n in notes]
        assert len(note_ids) == 3, f"Expected 3 test notes, got {len(note_ids)}"
        db.close()

    # 2. Call batch delete endpoint
    response = client.post('/api/notes/batch/delete', 
                           data=json.dumps({'note_ids': note_ids}),
                           content_type='application/json')

    # 3. Verify response
    assert response.status_code == 200, f"Batch delete failed: {response.json}"
    data = response.json
    assert data['status'] == 'success'
    assert data['data']['deleted_count'] == 3

    # 4. Verify test notes are deleted
    with app.app_context():
        db = sqlite3.connect(app.config['DATABASE'])
        count = db.execute("SELECT COUNT(*) FROM Notes WHERE title LIKE 'BatchDeleteTest%'").fetchone()[0]
        assert count == 0, "Test notes should be deleted"
        db.close()

