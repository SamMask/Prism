import re
import os

root_dir = r"c:\AI\Local Insight"
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

log_file = os.path.join(root_dir, "renumber_log.txt")

def log(msg):
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def update_version_string(match):
    full_str = match.group(0)
    major = int(match.group(1))
    rest = match.group(2)
    
    # Logic: v2.x -> v1.x, v1.x -> v0.x
    new_ver = full_str
    if major == 2:
        new_ver = f"v1{rest}"
    elif major == 1:
        new_ver = f"v0{rest}"
    
    # log(f"Replacing {full_str} with {new_ver}")
    return new_ver

def process_file(filename):
    filepath = os.path.join(root_dir, filename)
    if not os.path.exists(filepath):
        log(f"Skipping {filepath} (not found)")
        return

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        new_content = re.sub(r'v(\d+)(\.[0-9]+(?:\.[0-9]+)?)', update_version_string, content)
        
        if content != new_content:
            log(f"Updating {filename}...")
            # Use 'w' mode to overwrite
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
        else:
            log(f"No changes for {filename}")
            
    except Exception as e:
        log(f"Error processing {filename}: {e}")

if __name__ == "__main__":
    if os.path.exists(log_file):
        os.remove(log_file)
    log("Starting renumbering...")
    for f in files_to_update:
        process_file(f)
    log("Done.")
