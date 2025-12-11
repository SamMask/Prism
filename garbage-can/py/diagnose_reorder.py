import sys
import os
import traceback

# Add current directory to path
sys.path.append(os.getcwd())

from flask import Flask, jsonify, request
from db import get_db, close_db

# Mocking the app setup to isolate the issue
def create_test_app():
    app = Flask(__name__)
    app.config['DATABASE'] = os.path.join(os.getcwd(), 'knowledge.db')
    app.config['TESTING'] = True  # Critical: propagates exceptions

    # Register teardown
    app.teardown_appcontext(close_db)

    # Register blueprints (using the actual project code)
    try:
        from routes import register_blueprints
        register_blueprints(app)
        print("[DEBUG] Blueprints registered successfully")
    except Exception as e:
        print(f"[CRITICAL] Failed to register blueprints: {e}")
        traceback.print_exc()
    
    return app

if __name__ == "__main__":
    print("-" * 50)
    print("Starting Diagnosis Script for /api/notes/reorder")
    print("-" * 50)

    try:
        app = create_test_app()
        client = app.test_client()

        # Step 1: Check if Notes table has sort_order (Logic check)
        with app.app_context():
            db = get_db()
            cursor = db.execute("PRAGMA table_info(Notes)")
            cols = [col[1] for col in cursor.fetchall()]
            if 'sort_order' in cols:
                print(f"[PASS] 'sort_order' column exists in Notes table.")
            else:
                print(f"[FAIL] 'sort_order' column MISSING in Notes table!")

        # Step 2: Test the API Endpoint
        print("\n[TEST] Sending PUT request to /api/notes/reorder...")
        payload = {'note_ids': [1, 2, 3]} # Assuming these IDs exist or at least don't crash SQL syntax
        
        response = client.put('/api/notes/reorder', json=payload)
        
        print(f"[RESULT] Status Code: {response.status_code}")
        if response.status_code == 200:
            print(f"[SUCCESS] Response: {response.json}")
        else:
            print(f"[ERROR] Response Data: {response.data.decode('utf-8')}")
            
    except Exception as e:
        print("\n[EXCEPTION] An unexpected error occurred during testing:")
        traceback.print_exc()
