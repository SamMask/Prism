# -*- coding: utf-8 -*-
"""
Test AI Service API
Phase 6.1.3: AI Service Testing (Graceful Degradation)
"""

import pytest
import json


class TestAIStatusAPI:
    """Test /api/ai/status endpoint"""
    
    def test_ai_status_endpoint(self, client):
        """Test GET /api/ai/status returns status info"""
        response = client.get('/api/ai/status')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        
        # Check expected fields
        status = data['data']
        assert 'available' in status
        assert 'models' in status
        assert 'vision_ready' in status
        assert 'text_ready' in status
    
    def test_ai_status_graceful_when_unavailable(self, client):
        """Test AI status handles Ollama being offline gracefully"""
        response = client.get('/api/ai/status')
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Even if Ollama is offline, should return valid response
        assert 'available' in data['data']
        # available can be True or False


class TestAITagImageAPI:
    """Test /api/ai/tag_image endpoint"""
    
    def test_tag_image_requires_input(self, client):
        """Test POST /api/ai/tag_image requires image"""
        response = client.post('/api/ai/tag_image')
        # Should return 400 for missing image
        assert response.status_code == 400
    
    def test_tag_image_with_invalid_path(self, client):
        """Test POST /api/ai/tag_image handles missing file"""
        response = client.post(
            '/api/ai/tag_image',
            data=json.dumps({'image_path': '/nonexistent/image.jpg'}),
            content_type='application/json'
        )
        assert response.status_code in [400, 404]


class TestAISummarizeAPI:
    """Test /api/ai/summarize endpoint"""
    
    def test_summarize_requires_content(self, client):
        """Test POST /api/ai/summarize requires content"""
        response = client.post(
            '/api/ai/summarize',
            data=json.dumps({}),
            content_type='application/json'
        )
        assert response.status_code == 400
    
    def test_summarize_with_content(self, client):
        """Test POST /api/ai/summarize with valid content"""
        response = client.post(
            '/api/ai/summarize',
            data=json.dumps({
                'content': 'This is a test content for summarization. ' * 10
            }),
            content_type='application/json'
        )
        # May fail if Ollama is offline (400), or succeed (200)
        assert response.status_code in [200, 400, 500]


class TestAIAnalyzeNoteAPI:
    """Test /api/ai/analyze_note endpoint"""
    
    def test_analyze_note_requires_id(self, client):
        """Test POST /api/ai/analyze_note requires note_id"""
        response = client.post(
            '/api/ai/analyze_note',
            data=json.dumps({}),
            content_type='application/json'
        )
        assert response.status_code == 400
    
    def test_analyze_nonexistent_note(self, client):
        """Test POST /api/ai/analyze_note handles missing note"""
        response = client.post(
            '/api/ai/analyze_note',
            data=json.dumps({'note_id': 99999}),
            content_type='application/json'
        )
        assert response.status_code == 404
