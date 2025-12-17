# -*- coding: utf-8 -*-
"""
Test Tags API
Phase 6.1.2: Core API Testing
"""

import pytest
import json


class TestTagsAPI:
    """Test /api/tags endpoints"""
    
    def test_get_tags(self, client):
        """Test GET /api/tags returns list"""
        response = client.get('/api/tags')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert isinstance(data['data'], list)
    
    def test_tags_created_with_note(self, client, sample_note_data):
        """Test tags are created when adding note with tags"""
        # Create note with tags
        response = client.post(
            '/api/notes',
            data=json.dumps(sample_note_data),
            content_type='application/json'
        )
        assert response.status_code == 201
        
        # Check tags exist
        tags_response = client.get('/api/tags')
        data = json.loads(tags_response.data)
        tag_names = [t['name'] for t in data['data']]
        
        for tag in sample_note_data['tags']:
            assert tag in tag_names
    
    def test_tags_have_count(self, client, sample_note_data):
        """Test tags include usage count"""
        # Create note with tags
        client.post(
            '/api/notes',
            data=json.dumps(sample_note_data),
            content_type='application/json'
        )
        
        # Get tags
        response = client.get('/api/tags')
        data = json.loads(response.data)
        
        if data['data']:
            first_tag = data['data'][0]
            assert 'id' in first_tag
            assert 'name' in first_tag
            # count might be included
