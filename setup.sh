#!/bin/bash
echo -e "\033[96m[BAOTUE] Dang cap nhat he thong va cai dat Python...\033[0m"
yes | pkg update -y -o Dpkg::Options::="--force-confold"
yes | pkg upgrade -y -o Dpkg::Options::="--force-confold"
pkg install python curl -y
pip install --upgrade pip
pip install requests

echo -e "\033[96m[BAOTUE] Dang cap quyen truy cap bo nho (/sdcard) [Auto Yes]...\033[0m"
yes | termux-setup-storage
sleep 2

echo -e "\033[96m[BAOTUE] Dang tai file baotue.py vao /sdcard/Download...\033[0m"
curl -L -s -o /sdcard/Download/baotue.py https://raw.githubusercontent.com/baotuecoder999/BTHub/main/baotue.py

echo -e "\033[92m[BAOTUE] Cai dat hoan tat! Hay chay lenh buoc 3 de mo tool.\033[0m"
