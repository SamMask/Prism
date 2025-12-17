# -*- coding: utf-8 -*-
"""
Test Batch Tagging API
Phase 6.1.3: AI Service Testing
"""

import pytest
import json


class TestBatchTagAPI:
    """Test /api/ai/batch_tag endpoints"""
    
    def test_start_batch_tag(self, client):
        """Test POST /api/ai/batch_tag starts batch process"""
        response = client.post(
            '/api/ai/batch_tag',
            data=json.dumps({'scope': 'untagged'}),
            content_type='application/json'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'total' in data['data']
        assert 'message' in data['data']
    
    def test_batch_tag_scopes(self, client):
        """Test batch tag with different scopes"""
        scopes = ['all', 'untagged', 'category']
        
        for scope in scopes:
            payload = {'scope': scope}
            if scope == 'category':
                payload['category_id'] = 1  # Default category
            
            response = client.post(
                '/api/ai/batch_tag',
                data=json.dumps(payload),
                content_type='application/json'
            )
            assert response.status_code == 200, f"Scope {scope} failed"
    
    def test_get_batch_status(self, client):
        """Test GET /api/ai/batch_tag/<task_id> returns status"""
        # First start a batch task
        start_response = client.post(
            '/api/ai/batch_tag',
            data=json.dumps({'scope': 'untagged'}),
            content_type='application/json'
        )
        data = json.loads(start_response.data)
        task_id = data['data'].get('task_id')
        
        if task_id:
            # Get status
            response = client.get(f'/api/ai/batch_tag/{task_id}')
            assert response.status_code == 200
            status_data = json.loads(response.data)
            assert 'status' in status_data['data']
            assert 'progress' in status_data['data']
    
    def test_get_nonexistent_task_status(self, client):
        """Test getting status of non-existent task"""
        response = client.get('/api/ai/batch_tag/nonexistent123')
        assert response.status_code == 404
    
    def test_stop_batch_task(self, client, sample_note_data):
        """Test POST /api/ai/batch_tag/<task_id>/stop stops task"""
        # Create some notes to process
        for i in range(3):
            note = sample_note_data.copy()
            note['title'] = f'Batch Test {i}'
            note['tags'] = []  # No tags so they qualify for untagged scope
            client.post(
                '/api/notes',
                data=json.dumps(note),
                content_type='application/json'
            )
        
        # Start batch
        start_response = client.post(
            '/api/ai/batch_tag',
            data=json.dumps({'scope': 'untagged'}),
            content_type='application/json'
        )
        data = json.loads(start_response.data)
        task_id = data['data'].get('task_id')
        
        if task_id:
            # Stop it
            response = client.post(f'/api/ai/batch_tag/{task_id}/stop')
            assert response.status_code == 200
    
    def test_stop_nonexistent_task(self, client):
        """Test stopping non-existent task"""
        response = client.post('/api/ai/batch_tag/nonexistent123/stop')
        assert response.status_code == 404
