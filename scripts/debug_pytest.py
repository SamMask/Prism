
import pytest
import sys
import os

# Redirect stdout/stderr to a file
with open('pytest_debug_output.txt', 'w') as f:
    sys.stdout = f
    sys.stderr = f
    
    print("Running pytest collection...")
    try:
        ret = pytest.main(['--collect-only', 'tests'])
        print(f"\nPytest exit code: {ret}")
    except Exception as e:
        print(f"\nException: {e}")
