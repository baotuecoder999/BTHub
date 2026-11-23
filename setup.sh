#!/bin/bash
export DEBIAN_FRONTEND=noninteractive

echo -e "\033[96m[BAOTUE] Dang cap nhat he thong (Auto Yes)...\033[0m"
apt-get update -y
apt-get upgrade -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"

echo -e "\033[96m[BAOTUE] Dang cai dat Python, Curl va thu vien Requests...\033[0m"
apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" python curl python-pip
pip install --no-cache-dir requests || apt-get install -y python-requests

echo -e "\033[96m[BAOTUE] Dang cap quyen truy cap bo nho (/sdcard)...\033[0m"
printf "y\n" | termux-setup-storage
sleep 2

echo -e "\033[96m[BAOTUE] Dang tai file baotue.py vao /sdcard/Download...\033[0m"
mkdir -p /sdcard/Download
curl -L -s -o /sdcard/Download/baotue.py https://raw.githubusercontent.com/baotuecoder999/BTHub/main/baotue.py

echo -e "\033[92m[BAOTUE] Cai dat hoan tat! Hay chay lenh buoc 3 de mo tool.\033[0m"
