import re
import os

files_to_update = [
    'Local Insight.md',
    'SCHEMA.md',
    'TODO.md',
    'TestProject.md',
    'migrations/__init__.py',
    'db.py',
    'app.py',
    'DEPLOYMENT.md'
]

def update_version_string(match):
    full_str = match.group(0)
    major = int(match.group(1))
    rest = match.group(2) # .X or .X.Y
    
    if major == 2:
        return f"v1{rest}"
    elif major == 1:
        return f"v0{rest}"
    else:
        return full_str

def process_file(filepath):
    if not os.path.exists(filepath):
        print(f"Skipping {filepath} (not found)")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex to find vX.Y[.Z]
    # matches v1.0, v1.0.0, v2.0, etc.
    new_content = re.sub(r'v(\d+)(\.[0-9]+(?:\.[0-9]+)?)', update_version_string, content)
    
    # Also handle "Version X.Y" if present, but simpler to stick to vX.Y which is most common in these docs.
    # The user said "Local Insight v1.0". 
    # Let's also look for specific headers if they lack 'v'.
    
    if content != new_content:
        print(f"Updating {filepath}...")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
    else:
        print(f"No changes for {filepath}")

for f in files_to_update:
    process_file(f)
