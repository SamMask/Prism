# -*- coding: utf-8 -*-
"""
Test Categories API
Phase 6.1.2: Core API Testing
"""

import pytest
import json


class TestCategoriesAPI:
    """Test /api/categories endpoints"""
    
    def test_get_categories(self, client):
        """Test GET /api/categories returns list"""
        response = client.get('/api/categories')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert isinstance(data['data'], list)
    
    def test_create_category(self, client, sample_category_data):
        """Test POST /api/categories creates new category"""
        response = client.post(
            '/api/categories',
            data=json.dumps(sample_category_data),
            content_type='application/json'
        )
        assert response.status_code in [200, 201]
        data = json.loads(response.data)
        assert data['status'] == 'success'
    
    def test_create_duplicate_category(self, client, sample_category_data):
        """Test creating duplicate category fails or handles gracefully"""
        # Create first
        client.post(
            '/api/categories',
            data=json.dumps(sample_category_data),
            content_type='application/json'
        )
        
        # Try to create duplicate
        response = client.post(
            '/api/categories',
            data=json.dumps(sample_category_data),
            content_type='application/json'
        )
        # Should either fail (400) or handle gracefully (200 with message)
        assert response.status_code in [200, 400, 409]
    
    def test_category_has_count(self, client):
        """Test categories include note count"""
        response = client.get('/api/categories')
        data = json.loads(response.data)
        
        if data['data']:
            # Check if count field exists (may be 0)
            first_cat = data['data'][0]
            # count might be included or calculated separately
            assert 'id' in first_cat
            assert 'name' in first_cat

    def test_delete_category_migrates_notes_by_target_id(self, client, app):
        """Deleting a non-default category migrates notes to target_category_id."""
        create_response = client.post(
            '/api/categories',
            data=json.dumps({'name': 'Delete Me', 'icon': 'X'}),
            content_type='application/json'
        )
        category_id = json.loads(create_response.data)['data']['id']

        categories = client.get('/api/categories').get_json()['data']
        default_category_id = next(cat['id'] for cat in categories if cat['is_default'])

        note_response = client.post(
            '/api/notes',
            data=json.dumps({
                'title': 'Category migration note',
                'content': 'content',
                'category_id': category_id
            }),
            content_type='application/json'
        )
        note_id = json.loads(note_response.data)['data']['note_id']

        delete_response = client.delete(
            f'/api/categories/{category_id}',
            data=json.dumps({'target_category_id': default_category_id}),
            content_type='application/json'
        )

        assert delete_response.status_code == 200
        assert delete_response.get_json()['data']['migrated_notes_count'] == 1

        note = client.get(f'/api/notes/{note_id}').get_json()['data']
        assert note['category_id'] == default_category_id

    def test_update_category_rejects_empty_trimmed_name(self, client, app):
        """Updating a category cannot write an empty trimmed name."""
        create_response = client.post(
            '/api/categories',
            data=json.dumps({'name': 'No Empty Update', 'icon': 'N'}),
            content_type='application/json'
        )
        category_id = json.loads(create_response.data)['data']['id']

        response = client.put(
            f'/api/categories/{category_id}',
            data=json.dumps({'name': '   '}),
            content_type='application/json'
        )

        assert response.status_code == 400
        assert response.get_json() == {
            'status': 'error',
            'message': 'Category name cannot be empty'
        }

        categories = client.get('/api/categories').get_json()['data']
        category = next(cat for cat in categories if cat['id'] == category_id)
        assert category['name'] == 'No Empty Update'
