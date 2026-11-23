#!/bin/bash
clear
echo "=================================================="
echo "   DANG CAI DAT & KHOI CHAY TOOL BAOTUE.PY"
echo "=================================================="

# 1. Cap quyen bo nho & cai dat goi can thiet
termux-setup-storage
pkg update -y && pkg install -y python curl
pip install --break-system-packages --no-cache-dir requests

# 2. Tao thu muc va tai nguyen ban baotue.py
mkdir -p /sdcard/Download
curl -fsSL "https://raw.githubusercontent.com/baotuecoder999/BTHub/main/baotue.py" -o /sdcard/Download/baotue.py

# Kiem tra xem tai file co thanh cong khong (tranh loi 404)
if [ ! -s /sdcard/Download/baotue.py ] || grep -q "404: Not Found" /sdcard/Download/baotue.py; then
    echo "[LOI] Khong tai duoc baotue.py! Hay kiem tra lai ten file hoac che do Public cua repo BTHub."
    exit 1
fi

# 3. Tao lenh tat 'baotue' de lan sau mo nhanh
grep -q "alias baotue=" ~/.bashrc || echo 'alias baotue="cd /sdcard/Download && su -c \"python baotue.py\""' >> ~/.bashrc
source ~/.bashrc 2>/dev/null

# 4. Tu dong chay tool (ho tro ca may da Root va chua Root)
echo "[OK] Cai dat hoan tat! Dang mo tool..."
cd /sdcard/Download
if command -v su >/dev/null 2>&1 && su -c "id" >/dev/null 2>&1; then
    su -c "python baotue.py"
else
    python baotue.py
fi
