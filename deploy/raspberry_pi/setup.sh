#!/bin/bash
# =============================================================================
# Prism - Raspberry Pi / Headless Server Setup Script
# Phase 8.1: mDNS (avahi) + Reverse Proxy (Caddy) + systemd Service
#
# 使用方式:
#   cd /path/to/prism
#   bash deploy/raspberry_pi/setup.sh
#
# 功能:
#   1. 安裝 avahi-daemon → 讓區網其他裝置可用 http://prism.local 連線
#   2. 安裝 Caddy → 反向代理 80 port → Prism 5000 port
#   3. 建立 systemd 服務 → 開機自動啟動 Prism
#
# 冪等性: 可重複執行，不會破壞現有設定
# =============================================================================

set -euo pipefail

# --- 設定 ---
PRISM_HOSTNAME="${PRISM_HOSTNAME:-prism}"
PRISM_PORT="${PRISM_PORT:-5000}"
PRISM_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PRISM_USER="$(whoami)"
PYTHON_BIN="$(command -v python3 || command -v python)"

# 顏色輸出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info()    { echo -e "${GREEN}[✓]${NC} $*"; }
warn()    { echo -e "${YELLOW}[!]${NC} $*"; }
error()   { echo -e "${RED}[✗]${NC} $*" >&2; exit 1; }
section() { echo -e "\n${YELLOW}=== $* ===${NC}"; }

# --- 前置檢查 ---
section "前置檢查"

[[ "$(id -u)" -ne 0 ]] || error "請勿以 root 執行此腳本 (使用 sudo 的普通使用者即可)"

if ! command -v sudo &>/dev/null; then
    error "需要 sudo 權限，請先安裝 sudo"
fi

if [[ ! -f "$PRISM_DIR/app.py" ]]; then
    error "找不到 app.py，請確認腳本位於 Prism 專案的 deploy/raspberry_pi/ 目錄下"
fi

info "Prism 目錄: $PRISM_DIR"
info "執行使用者: $PRISM_USER"
info "Python 路徑: $PYTHON_BIN"
info "Prism 連接埠: $PRISM_PORT"
info "mDNS 主機名稱: $PRISM_HOSTNAME.local"

# --- Step 1: avahi-daemon (mDNS) ---
section "Step 1/3: 安裝並設定 avahi-daemon (mDNS)"

sudo apt-get update -qq
sudo apt-get install -y avahi-daemon avahi-utils

# 設定 hostname (冪等)
AVAHI_CONF="/etc/avahi/avahi-daemon.conf"
if sudo grep -q "^host-name=" "$AVAHI_CONF" 2>/dev/null; then
    sudo sed -i "s/^host-name=.*/host-name=$PRISM_HOSTNAME/" "$AVAHI_CONF"
elif sudo grep -q "^#host-name=" "$AVAHI_CONF" 2>/dev/null; then
    sudo sed -i "s/^#host-name=.*/host-name=$PRISM_HOSTNAME/" "$AVAHI_CONF"
else
    # [server] section 不存在 host-name 行時追加
    echo "host-name=$PRISM_HOSTNAME" | sudo tee -a "$AVAHI_CONF" >/dev/null
fi

sudo systemctl enable avahi-daemon
sudo systemctl restart avahi-daemon

# 等待 avahi 就緒
sleep 2
if avahi-resolve --name "${PRISM_HOSTNAME}.local" &>/dev/null; then
    info "mDNS 解析成功: ${PRISM_HOSTNAME}.local"
else
    warn "mDNS 設定完成，但解析需要數秒，稍後再測試: ping ${PRISM_HOSTNAME}.local"
fi

# --- Step 2: Caddy 反向代理 ---
section "Step 2/3: 安裝並設定 Caddy (反向代理)"

if ! command -v caddy &>/dev/null; then
    # 官方安裝方式 (Debian/Ubuntu/Raspberry Pi OS)
    sudo apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
        | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
        | sudo tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
    sudo apt-get update -qq
    sudo apt-get install -y caddy
fi

# 寫入 Caddyfile (冪等)
sudo tee /etc/caddy/Caddyfile >/dev/null <<EOF
# Prism - Reverse Proxy
# 將 80 port 流量導向 Prism 的 ${PRISM_PORT} port
:80 {
    reverse_proxy localhost:${PRISM_PORT}
}
EOF

sudo systemctl enable caddy
sudo systemctl restart caddy

info "Caddy 設定完成: port 80 → localhost:${PRISM_PORT}"

# --- Step 3: Prism systemd 服務 ---
section "Step 3/3: 建立 Prism systemd 服務"

sudo tee /etc/systemd/system/prism.service >/dev/null <<EOF
[Unit]
Description=Prism Knowledge Base Server
Documentation=https://github.com/$(git -C "$PRISM_DIR" remote get-url origin 2>/dev/null | sed 's/.*github.com[:/]//' | sed 's/\.git$//' || echo 'owner/prism')
After=network.target

[Service]
Type=simple
User=${PRISM_USER}
WorkingDirectory=${PRISM_DIR}
ExecStart=${PYTHON_BIN} app.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

# 環境變數
Environment=FLASK_DEBUG=False
Environment=PRISM_PORT=${PRISM_PORT}

# 安全強化
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable prism

# 若 Prism 已在執行則重啟，否則啟動
if sudo systemctl is-active --quiet prism; then
    sudo systemctl restart prism
    info "Prism 服務已重啟"
else
    sudo systemctl start prism
    info "Prism 服務已啟動"
fi

# --- 完成 ---
section "設定完成！"
echo ""
echo "  📡 區網連線: http://${PRISM_HOSTNAME}.local"
echo "  🔌 直接連線: http://$(hostname -I | awk '{print $1}'):${PRISM_PORT}"
echo ""
echo "常用指令:"
echo "  sudo systemctl status prism          # 查看 Prism 狀態"
echo "  sudo systemctl status caddy          # 查看代理狀態"
echo "  sudo journalctl -u prism -f          # 即時查看 Prism 日誌"
echo "  sudo journalctl -u caddy -f          # 即時查看 Caddy 日誌"
echo "  sudo systemctl restart prism         # 重啟 Prism"
echo ""
echo "環境變數覆蓋 (重新執行腳本前設定):"
echo "  PRISM_HOSTNAME=myprism bash deploy/raspberry_pi/setup.sh"
echo "  PRISM_PORT=8080    bash deploy/raspberry_pi/setup.sh"
