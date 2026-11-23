#!/data/data/com.termux/files/usr/bin/bash
clear
echo "=================================================="
echo "      CAI DAT & KHOI CHAY TOOL BAOTUE (CLOUD)     "
echo "=================================================="

GH_TOKEN="$1"
if [ -z "$GH_TOKEN" ]; then
    echo "[LOI] Thieu GitHub Token!"
    exit 1
fi

# 1. Cap quyen bo nho & cai dat goi can thiet (bo qua hoi y/n)
yes | termux-setup-storage >/dev/null 2>&1
pkg update -y >/dev/null 2>&1
pkg install -y python curl >/dev/null 2>&1
pip install --break-system-packages --no-cache-dir requests >/dev/null 2>&1

# 2. Xac dinh thu muc luu file tuong thich moi CloudPhone (UGPhone/Redfinger/VMOS)
if [ -w "/sdcard/Download" ]; then
    WORK_DIR="/sdcard/Download"
else
    mkdir -p "$HOME/baotue_app"
    WORK_DIR="$HOME/baotue_app"
fi

# 3. Tai baotue.py tu repo Private qua GitHub API
curl -fsSL \
  -H "Authorization: token $GH_TOKEN" \
  -H "Accept: application/vnd.github.v3.raw" \
  "https://api.github.com/repos/baotuecoder999/BTHub/contents/baotue.py" \
  -o "$WORK_DIR/baotue.py"

if [ ! -s "$WORK_DIR/baotue.py" ]; then
    echo "[LOI] Khong tai duoc baotue.py! Kiem tra lai Token hoac ten file trên GitHub."
    exit 1
fi

# 4. Lay duong dan Python chuan cua Termux & tao lenh tat 'baotue'
PY_BIN="/data/data/com.termux/files/usr/bin/python"
[ ! -x "$PY_BIN" ] && PY_BIN="$(command -v python)"

sed -i '/alias baotue=/d' ~/.bashrc 2>/dev/null
if command -v su >/dev/null 2>&1 && su -c "id" >/dev/null 2>&1; then
    echo "alias baotue='su -c \"$PY_BIN $WORK_DIR/baotue.py\"'" >> ~/.bashrc
    echo "[OK] Phat hien quyen ROOT! Dang mo tool..."
    su -c "$PY_BIN $WORK_DIR/baotue.py"
else
    echo "alias baotue='$PY_BIN $WORK_DIR/baotue.py'" >> ~/.bashrc
    echo "[OK] Che do NON-ROOT! Dang mo tool..."
    "$PY_BIN" "$WORK_DIR/baotue.py"
fi
