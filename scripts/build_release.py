
import os
import shutil
import subprocess
import sys
from datetime import datetime

# Configuration
APP_NAME = "Prism"
MAIN_SCRIPT = "app.py"
DIST_DIR = "dist"
BUILD_DIR = "build"
FRONTEND_DIR = os.path.join("frontend", "dist")

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def run_command(cmd, cwd=None):
    log(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, text=True)
    if result.returncode != 0:
        log(f"Error executing command: {cmd}")
        sys.exit(1)

def build_frontend():
    log("Building Frontend...")
    if not os.path.exists("frontend"):
        log("Frontend directory not found!")
        sys.exit(1)
    
    # Check if node_modules exists
    if not os.path.exists(os.path.join("frontend", "node_modules")):
        run_command("npm install", cwd="frontend")
    
    run_command("npm run build", cwd="frontend")

def clean_build_dirs():
    log("Cleaning previous build artifacts...")
    if os.path.exists(DIST_DIR):
        shutil.rmtree(DIST_DIR)
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    
    # Remove .spec file if exists
    if os.path.exists(f"{APP_NAME}.spec"):
        os.remove(f"{APP_NAME}.spec")

def create_executable():
    log("Creating Backend Executable with PyInstaller...")
    
    # Define data to include
    # Format: source;dest (Windows separator)
    add_data = [
        f"frontend/dist;frontend/dist",
        f"migrations;migrations",
        f"static;static",
        f"templates;templates",
    ]
    
    # Hidden imports needed for Flask, EngineIO, etc.
    hidden_imports = [
        "engineio.async_drivers.threading",
        # "numpy",
        # "sentence_transformers",
    ]
    
    # Construct PyInstaller command
    cmd = [
        "python", "-m", "PyInstaller",
        "--name", APP_NAME,
        "--onedir",
        "--windowed",
        "--clean",
        "--noconfirm",
        "--exclude-module", "numpy",
        "--exclude-module", "sentence_transformers",
    ]
    
    for item in add_data:
        cmd.extend(["--add-data", item])
        
    for item in hidden_imports:
        cmd.extend(["--hidden-import", item])
        
    cmd.append(MAIN_SCRIPT)
    
    run_command(" ".join(cmd))

def post_build_cleanup():
    log("Post-build cleanup and organization...")
    
    target_dir = os.path.join(DIST_DIR, APP_NAME)
    
    # Ensure uploads directory exists
    uploads_dir = os.path.join(target_dir, "static", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    
    # Create a start script with V2 + Desktop mode enabled
    with open(os.path.join(target_dir, "start_prism.bat"), "w") as f:
        f.write('@echo off\n')
        f.write('set PRISM_V2=1\n')
        f.write('set PRISM_DESKTOP=1\n')
        f.write('Prism.exe\n')
        
    log(f"Build completed successfully! Output is in: {target_dir}")

def main():
    log(f"Starting build process for {APP_NAME}...")
    
    clean_build_dirs()
    build_frontend()
    create_executable()
    post_build_cleanup()

if __name__ == "__main__":
    main()
