#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "========================================"
echo "  Prism - Go Primary Build"
echo "========================================"
echo

cd "$ROOT_DIR/frontend"
npm install
npm run build

cd "$ROOT_DIR"
rm -rf go-shadow/web/dist
mkdir -p go-shadow/web/dist build/go-runtime
cp -R frontend/dist/. go-shadow/web/dist/

cd go-shadow
go test ./...
go build -o ../build/go-runtime/prism-go-runtime .
GOOS=linux GOARCH=arm64 CGO_ENABLED=0 go build -o ../build/go-runtime/prism-go-runtime-linux-arm64 .

echo
echo "Build complete:"
echo "  build/go-runtime/prism-go-runtime"
echo "  build/go-runtime/prism-go-runtime-linux-arm64"
