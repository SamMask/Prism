
import pytest
import os
import shutil
from app import create_app, init_db

import tempfile

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # Create a temporary file to use as the database
    db_fd, db_path = tempfile.mkstemp()
    
    app = create_app('testing')
    # Override the DATABASE config to use the temporary file
    app.config['DATABASE'] = db_path
    
    # Initialize the database
    with app.app_context():
        init_db()
        
    yield app
    
    # Clean up
    os.close(db_fd)
    os.unlink(db_path)
    
    # Clean up test uploads directory
    test_upload_folder = app.config['UPLOAD_FOLDER']
    if os.path.exists(test_upload_folder) and 'test_uploads' in test_upload_folder:
        shutil.rmtree(test_upload_folder, ignore_errors=True)

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test runner for the app's CLI commands."""
    return app.test_cli_runner()
