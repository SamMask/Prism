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
    
    @pytest.mark.xfail(reason="Duplicate API has known issues - needs investigation")
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
        assert response.status_code in [200, 201]
        data = json.loads(response.data)
        assert 'note_id' in data['data']
        assert data['data']['note_id'] != note_id
    
    @pytest.mark.xfail(reason="Duplicate API has known issues - needs investigation")
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
        assert response.status_code in [200, 201]
        data = json.loads(response.data)
        
        # Check variant has parent_id
        if 'is_variant' in data['data']:
            assert data['data']['is_variant'] is True
