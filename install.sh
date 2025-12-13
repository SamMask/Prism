#!/bin/bash

echo "========================================"
echo "  Prism - Installation Script"
echo "========================================"
echo

echo "[1/2] Installing Python dependencies..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo
    echo "[ERROR] Failed to install dependencies."
    echo "Please make sure Python 3 and pip are installed."
    exit 1
fi

echo
echo "[2/2] Starting server..."
echo
echo "Server will start at: http://127.0.0.1:5000"
echo "Press Ctrl+C to stop the server."
echo

python3 app.py
