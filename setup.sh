#!/bin/bash
echo -e "\033[96m[BAOTUE] Dang cap nhat he thong va cai dat Python...\033[0m"
pkg update -y && pkg upgrade -y
pkg install python curl -y
pip install requests psutil

echo -e "\033[96m[BAOTUE] Dang cap quyen truy cap bo nho (/sdcard)...\033[0m"
termux-setup-storage
sleep 2

echo -e "\033[96m[BAOTUE] Dang tai file baotue.py vao /sdcard/Download...\033[0m"
curl -s -o /sdcard/Download/baotue.py https://raw.githubusercontent.com/baotuecoder999/BTHub/main/baotue.py

echo -e "\033[92m[BAOTUE] Cai dat hoan tat! Hay chay lenh buoc 3 de mo tool.\033[0m"
