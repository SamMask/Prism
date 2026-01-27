# -*- coding: utf-8 -*-
"""
Simple Test Runner - Bypasses pytest plugin issues
Run: python run_tests.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Block problematic web3 import before pytest loads
sys.modules['web3'] = None
sys.modules['web3.tools'] = None
sys.modules['web3.tools.pytest_ethereum'] = None

def run_api_tests():
    """Run basic API tests using Flask test client"""
    print("=" * 60)
    print("Prism V2 - API Test Runner")
    print("=" * 60)
    
    from app import create_app
    app = create_app('testing')
    
    app.config['TESTING'] = True
    client = app.test_client()
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: GET /api/notes
    print("\n[TEST] GET /api/notes...", end=" ")
    try:
        response = client.get('/api/notes')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"✗ FAILED: {e}")
        tests_failed += 1
    
    # Test 2: GET /api/categories
    print("[TEST] GET /api/categories...", end=" ")
    try:
        response = client.get('/api/categories')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"✗ FAILED: {e}")
        tests_failed += 1
    
    # Test 3: GET /api/tags
    print("[TEST] GET /api/tags...", end=" ")
    try:
        response = client.get('/api/tags')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"✗ FAILED: {e}")
        tests_failed += 1
    
    # Test 4: GET /api/ai/status
    print("[TEST] GET /api/ai/status...", end=" ")
    try:
        response = client.get('/api/ai/status')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"✗ FAILED: {e}")
        tests_failed += 1
    
    # Test 5: GET /api/search/status
    print("[TEST] GET /api/search/status...", end=" ")
    try:
        response = client.get('/api/search/status')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"✗ FAILED: {e}")
        tests_failed += 1
    
    # Test 6: POST /api/notes (Create)
    print("[TEST] POST /api/notes (Create)...", end=" ")
    try:
        import json
        response = client.post(
            '/api/notes',
            data=json.dumps({
                'title': 'Test Note',
                'content': 'Test content for automated testing'
            }),
            content_type='application/json'
        )
        assert response.status_code == 201, f"Expected 201, got {response.status_code}"
        data = json.loads(response.data)
        note_id = data['data']['note_id']
        print(f"✓ PASSED (note_id={note_id})")
        tests_passed += 1
        
        # Test 7: GET /api/notes/<id>
        print(f"[TEST] GET /api/notes/{note_id}...", end=" ")
        response = client.get(f'/api/notes/{note_id}')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ PASSED")
        tests_passed += 1
        
        # Test 8: DELETE /api/notes/<id>
        print(f"[TEST] DELETE /api/notes/{note_id}...", end=" ")
        response = client.delete(f'/api/notes/{note_id}')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ PASSED")
        tests_passed += 1
        
    except Exception as e:
        print(f"✗ FAILED: {e}")
        tests_failed += 1
    
    # Test 9: POST /api/ai/batch_tag
    print("[TEST] POST /api/ai/batch_tag...", end=" ")
    try:
        import json
        response = client.post(
            '/api/ai/batch_tag',
            data=json.dumps({'scope': 'untagged'}),
            content_type='application/json'
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ PASSED")
        tests_passed += 1
    except Exception as e:
        print(f"✗ FAILED: {e}")
        tests_failed += 1
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Tests: {tests_passed + tests_failed} | Passed: {tests_passed} | Failed: {tests_failed}")
    print("=" * 60)
    
    return tests_failed == 0


if __name__ == '__main__':
    success = run_api_tests()
    sys.exit(0 if success else 1)
