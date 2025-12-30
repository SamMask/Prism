
import pytest
import json
from app import create_app

@pytest.fixture
def client():
    app = create_app('testing')
    with app.test_client() as client:
        with app.app_context():
            # Ensure DB is initialized (testing usually uses separate in-memory DB or existing one)
            # For simplicity in this smoke test, we assume connection logic handles missing DB gracefully
            # or uses the existing knowledge.db if configured to do so (be careful not to write)
            pass
        yield client

def test_rag_search_payload_validation(client):
    """Test standard validation"""
    response = client.post('/api/rag/search', json={})
    assert response.status_code == 400
    
    response = client.post('/api/rag/search', json={'query': ''})
    assert response.status_code == 400

def test_rag_search_structure(client):
    """Test response structure (mocking vector store would be ideal, but let's try integration)"""
    # Note: If sentence-transformers is not available in the test env, this might fail with 503
    # We accept 503 as a valid "structure" check passing (meaning endpoint exists)
    
    response = client.post('/api/rag/search', json={'query': 'Prism', 'limit': 1})
    
    data = response.get_json()
    assert 'status' in data
    
    if response.status_code == 200:
        assert data['status'] == 'success'
        assert 'results' in data
        if len(data['results']) > 0:
            item = data['results'][0]
            assert 'content' in item
            assert 'score' in item
            assert 'source' in item
    elif response.status_code == 503:
        assert data['status'] == 'error'
        assert 'Vector search service not available' in data['message']
    else:
        # Other errors imply endpoint logic issues
        pytest.fail(f"Unexpected status code: {response.status_code}, {data}")
