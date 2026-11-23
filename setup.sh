#!/bin/bash
clear
echo "=================================================="
echo "   DANG CAI DAT & KHOI CHAY TOOL BAOTUE.PY"
echo "=================================================="

GH_TOKEN="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"
if [ -z "$GH_TOKEN" ]; then
    echo "[LOI] Thieu GitHub Token!"
    exit 1
fi

termux-setup-storage
pkg update -y && pkg install -y python curl
pip install --break-system-packages --no-cache-dir requests

mkdir -p /sdcard/Download
curl -fsSL \
  -H "Authorization: Bearer $GH_TOKEN" \
  -H "Accept: application/vnd.github.v3.raw" \
  "https://api.github.com/repos/baotuecoder999/BTHub/contents/baotue.py" \
  -o /sdcard/Download/baotue.py

if [ ! -s /sdcard/Download/baotue.py ]; then
    echo "[LOI] Khong tai duoc baotue.py tu repo Private! Kiem tra lai ten file 'baotue.py' tren repo."
    exit 1
fi

grep -q "alias baotue=" ~/.bashrc || echo 'alias baotue="cd /sdcard/Download && su -c \"python baotue.py\""' >> ~/.bashrc
source ~/.bashrc 2>/dev/null

echo "[OK] Cai dat hoan tat! Dang mo tool..."
cd /sdcard/Download
if command -v su >/dev/null 2>&1 && su -c "id" >/dev/null 2>&1; then
    su -c "python baotue.py"
else
    python baotue.py
fi
