import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from db import init_db

print("🔄 Manually initializing database...")
try:
    with app.app_context():
        init_db()
        # Verify file exists
        db_path = app.config['DATABASE']
        if os.path.exists(db_path):
            print(f"✅ Database created at: {db_path}")
            print(f"   Size: {os.path.getsize(db_path)} bytes")
        else:
            print(f"❌ Database file not found at: {db_path}")
            
except Exception as e:
    print(f"❌ Error: {e}")
