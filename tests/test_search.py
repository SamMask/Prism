# -*- coding: utf-8 -*-
"""
Test Search API
Phase 6.1.2: Core API Testing
"""

import pytest
import json


class TestSearchAPI:
    """Test /api/search endpoints"""
    
    def test_semantic_search_status(self, client):
        """Test GET /api/search/status returns service status"""
        response = client.get('/api/search/status')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'available' in data['data']
        assert 'model_name' in data['data']
    
    def test_semantic_search_requires_query(self, client):
        """Test GET /api/search/semantic requires q parameter"""
        response = client.get('/api/search/semantic')
        # Should return 400 or empty result
        assert response.status_code in [200, 400]
    
    def test_semantic_search_with_query(self, client, sample_note_data):
        """Test GET /api/search/semantic with query"""
        # Create a note first
        client.post(
            '/api/notes',
            data=json.dumps(sample_note_data),
            content_type='application/json'
        )
        
        # Search for it
        response = client.get('/api/search/semantic?q=test')
        assert response.status_code == 200
        data = json.loads(response.data)
        # May have results or not depending on embedding status
        assert data['status'] == 'success'
    
    def test_hybrid_search(self, client, sample_note_data):
        """Test GET /api/search/hybrid endpoint"""
        # Create a note
        client.post(
            '/api/notes',
            data=json.dumps(sample_note_data),
            content_type='application/json'
        )
        
        # Test hybrid search
        response = client.get('/api/search/hybrid?q=test')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
    
    def test_search_with_different_modes(self, client):
        """Test search modes: hybrid, fts, vector"""
        modes = ['hybrid', 'fts', 'vector']
        
        for mode in modes:
            response = client.get(f'/api/search/hybrid?q=test&mode={mode}')
            assert response.status_code == 200, f"Mode {mode} failed"


class TestIndexAPI:
    """Test /api/index endpoints"""
    
    def test_rebuild_index(self, client):
        """Test POST /api/index/rebuild triggers index rebuild"""
        response = client.post('/api/index/rebuild')
        # May take time, but should return success or processing status
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
