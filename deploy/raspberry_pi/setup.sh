#!/bin/bash
# =============================================================================
# Prism - Raspberry Pi / Headless Server Setup Script
#
# Current production owner: Go primary runtime.
# This script configures mDNS, Caddy, and prism-go-primary.service only.
# The Go linux/arm64 artifact is normally uploaded by scripts/go_primary_pi_live_ops.ps1.
# =============================================================================

set -euo pipefail

PRISM_HOSTNAME="${PRISM_HOSTNAME:-prism}"
PRISM_PORT="${PRISM_PORT:-5004}"
PRISM_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PRISM_USER="$(whoami)"
PRISM_LIVE_DIR="${PRISM_LIVE_DIR:-$PRISM_DIR/go-primary-live}"
PRISM_BIN="${PRISM_BIN:-$PRISM_LIVE_DIR/bin/prism-go-runtime-linux-arm64}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()    { echo -e "${GREEN}[ok]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*"; }
error()   { echo -e "${RED}[x]${NC} $*" >&2; exit 1; }
section() { echo -e "\n${YELLOW}=== $* ===${NC}"; }

section "Preflight"

[[ "$(id -u)" -ne 0 ]] || error "Do not run as root; run as the target Prism user with sudo available."
command -v sudo >/dev/null 2>&1 || error "sudo is required."

if [[ ! -x "$PRISM_BIN" ]]; then
    error "Missing executable Go runtime: $PRISM_BIN. Upload/build it first with scripts/go_primary_pi_live_ops.ps1."
fi
if [[ ! -f "$PRISM_DIR/knowledge.db" ]]; then
    error "Missing live database: $PRISM_DIR/knowledge.db"
fi

info "Prism dir: $PRISM_DIR"
info "Go binary: $PRISM_BIN"
info "Service port: $PRISM_PORT"
info "mDNS host: $PRISM_HOSTNAME.local"

section "Install avahi-daemon"

sudo apt-get update -qq
sudo apt-get install -y avahi-daemon avahi-utils

AVAHI_CONF="/etc/avahi/avahi-daemon.conf"
if sudo grep -q "^host-name=" "$AVAHI_CONF" 2>/dev/null; then
    sudo sed -i "s/^host-name=.*/host-name=$PRISM_HOSTNAME/" "$AVAHI_CONF"
elif sudo grep -q "^#host-name=" "$AVAHI_CONF" 2>/dev/null; then
    sudo sed -i "s/^#host-name=.*/host-name=$PRISM_HOSTNAME/" "$AVAHI_CONF"
else
    echo "host-name=$PRISM_HOSTNAME" | sudo tee -a "$AVAHI_CONF" >/dev/null
fi

sudo systemctl enable avahi-daemon
sudo systemctl restart avahi-daemon

section "Install Caddy"

if ! command -v caddy >/dev/null 2>&1; then
    sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
        | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
        | sudo tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
    sudo apt-get update -qq
    sudo apt-get install -y caddy
fi

sudo tee /etc/caddy/Caddyfile >/dev/null <<EOF
http://${PRISM_HOSTNAME}.local {
    redir https://${PRISM_HOSTNAME}.local{uri} permanent
}

https://${PRISM_HOSTNAME}.local {
    tls internal
    reverse_proxy 127.0.0.1:${PRISM_PORT} {
        header_down X-Prism-Go-Primary hit
    }
}
EOF

sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl enable caddy
sudo systemctl restart caddy
info "Caddy routes https://${PRISM_HOSTNAME}.local to 127.0.0.1:${PRISM_PORT}"

section "Install prism-go-primary.service"

sudo tee /etc/systemd/system/prism-go-primary.service >/dev/null <<EOF
[Unit]
Description=Prism Go Primary Runtime
After=network.target

[Service]
Type=simple
User=${PRISM_USER}
WorkingDirectory=${PRISM_DIR}
ExecStart=${PRISM_BIN} --db ${PRISM_DIR}/knowledge.db --data-dir ${PRISM_DIR} --addr 127.0.0.1:${PRISM_PORT} --enable-tag-write --enable-category-write --enable-notes-write --enable-attachment-text-read --enable-attachment-raw-read --enable-attachment-write --enable-upload-write --enable-thumbnail-write --enable-upload-url-write --enable-upload-delete --enable-media-cleanup --enable-import-export --enable-server-system
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=PRISM_GO_ALLOW_PROD_DB=1
Environment=PRISM_GO_ALLOW_PROD_UPLOADS=1
Environment=PRISM_GO_ALLOW_PROD_IMPORT_EXPORT=1
Environment=PRISM_GO_ALLOW_PROD_SERVER_SYSTEM=1
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now prism-go-primary.service

if sudo systemctl list-unit-files prism.service >/dev/null 2>&1; then
    sudo systemctl disable --now prism.service >/dev/null 2>&1 || true
    warn "Disabled legacy prism.service; keep it only as a rollback artifact until T046."
fi

section "Verify"
sudo systemctl is-active prism-go-primary.service
curl -skI "https://${PRISM_HOSTNAME}.local/api/server/version" | tr -d '\r' | grep -Ei 'HTTP|X-Prism-Go-Primary' || true

echo
info "Setup complete: https://${PRISM_HOSTNAME}.local"
