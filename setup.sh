#!/bin/bash
clear
echo "[⏳] Đang cài đặt môi trường cho BAOTUE Tool..."
termux-setup-storage
pkg update -y && pkg install -y python curl
pip install --break-system-packages --no-cache-dir requests
mkdir -p /sdcard/Download
curl -sL "https://raw.githubusercontent.com/baotuecoder999/BTHub/main/baotue.py" -o /sdcard/Download/baotue.py
echo 'alias baotue="cd /sdcard/Download && su -c \"python baotue.py\""' >> ~/.bashrc
echo "[✔] Cài đặt xong! Đang khởi chạy tool..."
cd /sdcard/Download && su -c "python baotue.py"
