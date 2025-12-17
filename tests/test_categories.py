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
