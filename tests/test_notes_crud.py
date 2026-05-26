# -*- coding: utf-8 -*-
"""
Test Notes CRUD API
Phase 6.1.2: Core API Testing
"""

import pytest
import json


class TestNotesAPI:
    """Test /api/notes endpoints"""
    
    def test_get_notes_empty(self, client):
        """Test GET /api/notes returns empty list for new DB"""
        response = client.get('/api/notes')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'data' in data
        assert isinstance(data['data'], list)
    
    def test_create_note(self, client, sample_note_data):
        """Test POST /api/notes creates a new note"""
        response = client.post(
            '/api/notes',
            data=json.dumps(sample_note_data),
            content_type='application/json'
        )
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'note_id' in data['data']
        assert data['data']['note_id'] > 0
    
    def test_get_single_note(self, client, sample_note_data):
        """Test GET /api/notes/<id> returns the created note"""
        # First create a note
        create_response = client.post(
            '/api/notes',
            data=json.dumps(sample_note_data),
            content_type='application/json'
        )
        note_id = json.loads(create_response.data)['data']['note_id']
        
        # Then get it
        response = client.get(f'/api/notes/{note_id}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert data['data']['id'] == note_id
        assert data['data']['title'] == sample_note_data['title']
    
    def test_update_note(self, client, sample_note_data):
        """Test PUT /api/notes/<id> updates the note"""
        # Create a note
        create_response = client.post(
            '/api/notes',
            data=json.dumps(sample_note_data),
            content_type='application/json'
        )
        note_id = json.loads(create_response.data)['data']['note_id']
        
        # Update it
        updated_data = sample_note_data.copy()
        updated_data['title'] = 'Updated Title'
        updated_data['content'] = 'Updated content'
        
        response = client.put(
            f'/api/notes/{note_id}',
            data=json.dumps(updated_data),
            content_type='application/json'
        )
        assert response.status_code == 200
        
        # Verify update
        get_response = client.get(f'/api/notes/{note_id}')
        data = json.loads(get_response.data)
        assert data['data']['title'] == 'Updated Title'
    
    def test_delete_note(self, client, sample_note_data):
        """Test DELETE /api/notes/<id> removes the note"""
        # Create a note
        create_response = client.post(
            '/api/notes',
            data=json.dumps(sample_note_data),
            content_type='application/json'
        )
        note_id = json.loads(create_response.data)['data']['note_id']
        
        # Delete it
        response = client.delete(f'/api/notes/{note_id}')
        assert response.status_code == 200
        
        # Verify deletion
        get_response = client.get(f'/api/notes/{note_id}')
        assert get_response.status_code == 404
    
    def test_get_notes_with_pagination(self, client, sample_note_data):
        """Test GET /api/notes supports pagination"""
        # Create multiple notes
        for i in range(5):
            note = sample_note_data.copy()
            note['title'] = f'Note {i}'
            client.post(
                '/api/notes',
                data=json.dumps(note),
                content_type='application/json'
            )
        
        # Test pagination
        response = client.get('/api/notes?page=1&per_page=2')
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'pagination' in data
        assert data['pagination']['per_page'] == 2

    def test_get_notes_archived_and_pinned_filters(self, client):
        """Test GET /api/notes supports archived and pinned filters."""
        archived_response = client.post(
            '/api/notes',
            data=json.dumps({
                'title': 'Archived Note',
                'content': 'archived content',
                'is_archived': True
            }),
            content_type='application/json'
        )
        archived_id = json.loads(archived_response.data)['data']['note_id']

        pinned_response = client.post(
            '/api/notes',
            data=json.dumps({
                'title': 'Pinned Note',
                'content': 'pinned content',
                'is_pinned': True
            }),
            content_type='application/json'
        )
        pinned_id = json.loads(pinned_response.data)['data']['note_id']

        archived_list = client.get('/api/notes?archived=true').get_json()['data']
        assert {note['id'] for note in archived_list} == {archived_id}

        default_list = client.get('/api/notes').get_json()['data']
        assert archived_id not in {note['id'] for note in default_list}

        pinned_list = client.get('/api/notes?pinned_only=true').get_json()['data']
        assert pinned_id in {note['id'] for note in pinned_list}
        assert all(note['is_pinned'] for note in pinned_list)

    def test_search_matches_note_fields_tags_and_attachment_content(
        self,
        client,
        app,
        tmp_path,
        monkeypatch
    ):
        """Test GET /api/notes?q= searches all user-visible card fields."""
        monkeypatch.setattr(app, 'root_path', str(tmp_path))

        def create_note(title, content, **overrides):
            payload = {
                'title': title,
                'content': content,
                **overrides,
            }
            response = client.post(
                '/api/notes',
                data=json.dumps(payload),
                content_type='application/json'
            )
            assert response.status_code == 201
            return json.loads(response.data)['data']['note_id']

        expected = {
            'titlealpha': create_note('titlealpha card', 'ordinary body'),
            'bodyalpha': create_note('ordinary title', 'bodyalpha text'),
            'remarkalpha': create_note(
                'remark card',
                'ordinary body',
                remarks='remarkalpha note'
            ),
            'tagalpha': create_note(
                'tag card',
                'ordinary body',
                tags=['tagalpha']
            ),
            'attachmentalpha': create_note('attachment card', 'ordinary body'),
        }

        attachment_dir = tmp_path / 'docs' / 'attachments'
        attachment_dir.mkdir(parents=True)
        attachment_path = attachment_dir / 'search_fixture.md'
        attachment_path.write_text(
            '# Search Fixture\n\nattachmentalpha appears only in this file.',
            encoding='utf-8'
        )

        with app.app_context():
            from db import get_db
            db = get_db()
            db.execute(
                '''
                INSERT INTO Note_Attachments (
                    note_id, file_path, file_type, title, size_bytes
                )
                VALUES (?, ?, 'md', ?, ?)
                ''',
                (
                    expected['attachmentalpha'],
                    'docs/attachments/search_fixture.md',
                    'Attachment Fixture',
                    attachment_path.stat().st_size
                )
            )
            db.commit()

        for keyword, note_id in expected.items():
            response = client.get(f'/api/notes?q={keyword}&per_page=100')
            assert response.status_code == 200
            result_ids = {note['id'] for note in response.get_json()['data']}
            assert note_id in result_ids
    
    def test_create_note_missing_content(self, client):
        """Test POST /api/notes fails without content"""
        response = client.post(
            '/api/notes',
            data=json.dumps({'title': 'No Content'}),
            content_type='application/json'
        )
        assert response.status_code == 400
    
    def test_get_nonexistent_note(self, client):
        """Test GET /api/notes/<id> returns 404 for missing note"""
        response = client.get('/api/notes/99999')
        assert response.status_code == 404


class TestNoteActions:
    """Test note action endpoints"""

    def test_duplicate_note(self, client, sample_note_data):
        """Test POST /api/notes/<id>/duplicate creates a copy"""
        # Create original
        create_response = client.post(
            '/api/notes',
            data=json.dumps(sample_note_data),
            content_type='application/json'
        )
        note_id = json.loads(create_response.data)['data']['note_id']
        
        # Duplicate
        response = client.post(f'/api/notes/{note_id}/duplicate')
        assert response.status_code == 201
        data = json.loads(response.data)
        assert 'note_id' in data['data']
        assert data['data']['note_id'] != note_id

        duplicate_id = data['data']['note_id']
        get_response = client.get(f'/api/notes/{duplicate_id}')
        get_data = json.loads(get_response.data)
        assert get_response.status_code == 200
        assert get_data['data']['title'].endswith(' (Copy)')

    def test_duplicate_as_variant(self, client, sample_note_data):
        """Test creating a variant with parent_id linkage"""
        # Create original
        create_response = client.post(
            '/api/notes',
            data=json.dumps(sample_note_data),
            content_type='application/json'
        )
        note_id = json.loads(create_response.data)['data']['note_id']
        
        # Create variant
        response = client.post(
            f'/api/notes/{note_id}/duplicate',
            data=json.dumps({'as_variant': True}),
            content_type='application/json'
        )
        assert response.status_code == 201
        data = json.loads(response.data)

        assert data['data']['is_variant'] is True
        assert data['data']['parent_id'] == note_id

        variant_id = data['data']['note_id']
        get_response = client.get(f'/api/notes/{variant_id}')
        get_data = json.loads(get_response.data)
        assert get_response.status_code == 200
        assert get_data['data']['parent_id'] == note_id
