#!/data/data/com.termux/files/usr/bin/bash
clear
echo "=================================================="
echo "      CAI DAT & KHOI CHAY TOOL BAOTUE (REJOIN)     "
echo "=================================================="

# 1. Cap quyen bo nho & cai dat moi truong tu dong
yes | termux-setup-storage >/dev/null 2>&1
pkg update -y >/dev/null 2>&1
pkg install -y python curl >/dev/null 2>&1
pip install --break-system-packages --no-cache-dir requests >/dev/null 2>&1

# 2. Chon thu muc luu file an toan cho moi CloudPhone
if [ -w "/sdcard/Download" ]; then
    WORK_DIR="/sdcard/Download"
else
    mkdir -p "$HOME/baotue_app"
    WORK_DIR="$HOME/baotue_app"
fi

# 3. Tai baotue.py tu repo Public BTHub (kem chong cache)
curl -fsSL "https://raw.githubusercontent.com/baotuecoder999/BTHub/main/baotue.py?t=$(date +%s)" -o "$WORK_DIR/baotue.py"

if [ ! -s "$WORK_DIR/baotue.py" ]; then
    echo "[LOI] Khong tai duoc baotue.py! Kiem tra lai ket noi mang hoac repo BTHub."
    exit 1
fi

# 4. Tao lenh tat 'baotue' & khoi chay tool ngay lap tuc
PY_BIN="/data/data/com.termux/files/usr/bin/python"
[ ! -x "$PY_BIN" ] && PY_BIN="$(command -v python)"

sed -i '/alias baotue=/d' ~/.bashrc 2>/dev/null
if command -v su >/dev/null 2>&1 && su -c "id" >/dev/null 2>&1; then
    echo "alias baotue='su -c \"$PY_BIN $WORK_DIR/baotue.py\"'" >> ~/.bashrc
    echo "[OK] Che do ROOT san sang! Dang mo tool..."
    su -c "$PY_BIN $WORK_DIR/baotue.py"
else
    echo "alias baotue='$PY_BIN $WORK_DIR/baotue.py'" >> ~/.bashrc
    echo "[OK] Che do NON-ROOT san sang! Dang mo tool..."
    "$PY_BIN" "$WORK_DIR/baotue.py"
fi
