import os
import time
import json
import requests

CFG_PATH = "/sdcard/Download/baotue_config.json"

# --- BẢNG MÀU & ĐỊNH DẠNG ANSI ---
C_CYAN = "\033[96m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_RED = "\033[91m"
C_PURPLE = "\033[95m"
C_WHITE = "\033[97m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_RESET = "\033[0m"

def load_cfg():
    if os.path.exists(CFG_PATH):
        with open(CFG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if data.get("packages") and isinstance(data["packages"][0], str):
                data["packages"] = [{"pkg": p, "active": True} for p in data["packages"]]
            return data
    return {"game_id": "2753915549", "delay": 20, "packages": [], "accounts": []}

def save_cfg(data):
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def get_system_stats():
    ram_percent = 0
    cpu_percent = 0
    try:
        with open("/proc/meminfo", "r") as f:
            lines = f.readlines()
            mem_total = int(lines[0].split()[1])
            mem_available = int(lines[2].split()[1]) if len(lines) > 2 else int(lines[1].split()[1])
            ram_used = mem_total - mem_available
            ram_percent = int((ram_used / mem_total) * 100)
    except Exception:
        ram_percent = 0

    try:
        top_out = os.popen("top -n 1 -b 2>/dev/null | grep -i 'cpu'").read().strip()
        if not top_out:
            top_out = os.popen("top -n 1 -d 1 2>/dev/null").read()
        for line in top_out.splitlines():
            if "cpu" in line.lower() or "%cpu" in line.lower():
                parts = line.replace(",", " ").split()
                for p in parts:
                    if "%" in p and p.replace("%", "").replace(".", "").isdigit():
                        cpu_percent = float(p.replace("%", ""))
                        break
        if cpu_percent == 0:
            load_avg = os.getloadavg()[0] if hasattr(os, "getloadavg") else 1.0
            cpu_percent = min(int(load_avg * 25), 100)
    except Exception:
        cpu_percent = 0

    return f"{cpu_percent}%", f"{ram_percent}%"

def scan_packages():
    found = set()
    q_out = os.popen('cmd package query-activities -a android.intent.action.VIEW -d "roblox://" 2>/dev/null').read()
    for line in q_out.splitlines():
        line = line.strip()
        if line.startswith("packageName="):
            pkg = line.split("=", 1)[1].strip()
            if pkg:
                found.add(pkg)

    keywords = ["roblox", "delta", "arceus", "codex", "fluxus", "hydrogen", "vega", "trigon", "evon", "noka"]
    all_pkgs = os.popen("pm list packages -3").read().splitlines()
    for line in all_pkgs:
        pkg = line.replace("package:", "").strip()
        if any(k in pkg.lower() for k in keywords):
            found.add(pkg)

    return sorted(list(found))

def verify_cookie(cookie):
    try:
        cookie = cookie.strip().strip('"').strip("'")
        if ".ROBLOSECURITY=" in cookie:
            cookie = cookie.split(".ROBLOSECURITY=")[1].split(";")[0]

        r = requests.get(
            "https://users.roblox.com/v1/users/authenticated",
            cookies={".ROBLOSECURITY": cookie},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            return str(data["id"]), data["name"], cookie
    except Exception:
        pass
    return None, None, None

def is_in_game(user_id):
    if not user_id:
        return None
    try:
        r = requests.post(
            "https://presence.roblox.com/v1/presence/users",
            json={"userIds": [int(user_id)]},
            timeout=10
        )
        if r.status_code == 200:
            return r.json()["userPresences"][0]["userPresenceType"] == 2
    except Exception:
        pass
    return False

def get_auth_ticket(cookie):
    if not cookie:
        return None
    try:
        s = requests.Session()
        s.cookies[".ROBLOSECURITY"] = cookie
        headers = {
            "User-Agent": "Roblox/WinInet",
            "Referer": "https://www.roblox.com/"
        }
        r1 = s.post("https://auth.roblox.com/v1/authentication-ticket", headers=headers, timeout=10)
        csrf = r1.headers.get("x-csrf-token")
        if csrf:
            headers["x-csrf-token"] = csrf
        
        r2 = s.post("https://auth.roblox.com/v1/authentication-ticket", headers=headers, timeout=10)
        ticket = r2.headers.get("rbx-authentication-ticket")
        return ticket
    except Exception:
        return None

def launch_package_tab(pkg, game_id, acc_info=None):
    display_name = acc_info["name"] if acc_info else "Chưa gắn Cookie"
    print(f"\n{C_YELLOW}{C_BOLD}  [⏳] ĐANG KHỞI ĐỘNG TAB: {pkg}{C_RESET}")
    print(f"       {C_WHITE}• Tài khoản : {C_PURPLE}{display_name}{C_RESET}")
    print(f"       {C_WHITE}• Join Game : {C_CYAN}{game_id}{C_RESET}")
    
    # Ép đóng ứng dụng trước khi mở mới
    os.system(f"am force-stop {pkg} 2>/dev/null || su -c 'am force-stop {pkg}'")
    time.sleep(2)
    
    if acc_info and acc_info.get("cookie"):
        cookie = acc_info["cookie"]
        ticket = get_auth_ticket(cookie)
        
        # Cơ chế bơm trực tiếp Cookie vào thư mục nội bộ của App (Hỗ trợ các bản mod như Noka, Delta)
        # Tạo file SharedPreferences hoặc WebView cookies giả lập để app tự nhận diện tài khoản
        inject_cmd = f"""su -c '
        mkdir -p /data/data/{pkg}/app_webview/Default/
        cat << "EOF" > /data/data/{pkg}/app_webview/Default/Cookies
        # Netscape HTTP Cookie File
        .roblox.com\tTRUE\t/\tTRUE\t0\t.ROBLOSECURITY\t{cookie}
        EOF
        chmod -R 777 /data/data/{pkg}/app_webview/
        '"""
        os.system(inject_cmd)

        if ticket:
            # Gửi đồng thời cả URL Ticket và đánh thức Intent của Client Mod
            url = f"roblox://placeId={game_id}&ticket={ticket}"
            os.system(f'am start -p {pkg} -a android.intent.action.VIEW -d "{url}" > /dev/null 2>&1')
            print(f"{C_GREEN}{C_BOLD}  [✔] ĐÃ BƠM COOKIE & GỬI VÉ JOIN GAME ID {game_id}!{C_RESET}")
            return
        else:
            print(f"{C_RED}{C_BOLD}  [⚠] Không lấy được Ticket, đang mở trực tiếp App bằng Cookie nội bộ...{C_RESET}")

    # Mở trực tiếp App nếu không có cookie
    url_direct = f"roblox://placeId={game_id}"
    os.system(f'am start -p {pkg} -a android.intent.action.VIEW -d "{url_direct}" > /dev/null 2>&1')
    print(f"{C_GREEN}{C_BOLD}  [✔] ĐÃ MỞ APP & JOIN THẲNG VÀO GAME ID {game_id}!{C_RESET}")

def run_auto_rejoin(cfg):
    active_pkgs = [p["pkg"] for p in cfg.get("packages", []) if p.get("active", True)]
    if not active_pkgs:
        print(f"\n{C_RED}{C_BOLD}  [!] BẠN CHƯA CHỌN PACKAGE NÀO ĐỂ CHẠY!{C_RESET}")
        print(f"{C_YELLOW}  ➔ Hãy vào mục [2] để BẬT các Package cần chạy trên CloudPhone.{C_RESET}")
        time.sleep(3)
        return

    acc_map = {a["pkg"]: a for a in cfg.get("accounts", [])}
    
    os.system("clear")
    print(f"{C_CYAN}{C_BOLD}╔════════════════════════════════════════════════════════════════════════════╗{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}║                 🚀 HỆ THỐNG AUTO-REJOIN ĐANG HOẠT ĐỘNG 🚀                  ║{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}╚════════════════════════════════════════════════════════════════════════════╝{C_RESET}\n")
    print(f"  {C_YELLOW}{C_BOLD}• ID GAME MỤC TIÊU   :{C_RESET} {C_GREEN}{C_BOLD}{cfg['game_id']}{C_RESET}")
    print(f"  {C_YELLOW}{C_BOLD}• SỐ PACKAGE ĐÃ CHỌN :{C_RESET} {C_WHITE}{C_BOLD}{len(active_pkgs)} tab đang kích hoạt{C_RESET}")
    print(f"  {C_YELLOW}{C_BOLD}• CHU KỲ KIỂM TRA    :{C_RESET} {C_WHITE}{C_BOLD}{cfg.get('delay', 20)} giây / lần{C_RESET}\n")
    print(f"{C_CYAN}──────────────────────────────────────────────────────────────────────────────{C_RESET}")

    for pkg in active_pkgs:
        launch_package_tab(pkg, cfg["game_id"], acc_map.get(pkg))
        time.sleep(6)

    print(f"\n{C_GREEN}{C_BOLD}  [⚡] ĐÃ KHỞI ĐỘNG XONG! BẮT ĐẦU GIÁM SÁT TỰ ĐỘNG...{C_RESET}")
    print(f"{C_YELLOW}  (Nhấn tổ hợp phím Ctrl + C để dừng và quay về Menu chính){C_RESET}\n")
    
    try:
        while True:
            print(f"{C_DIM}──────────────────────────────────────────────────────────────────────────────{C_RESET}")
            print(f"{C_CYAN}{C_BOLD}  [⏰ KIỂM TRA LÚC: {time.strftime('%H:%M:%S')}]{C_RESET}\n")
            for pkg in active_pkgs:
                acc = acc_map.get(pkg)
                pid = os.popen(f"pidof {pkg}").read().strip()
                
                if acc and acc.get("uid"):
                    ingame = is_in_game(acc["uid"])
                    if not pid or not ingame:
                        reason = "Tắt ứng dụng" if not pid else "Bị văng khỏi phòng / Mất kết nối"
                        print(f"{C_RED}{C_BOLD}  [⚠ PHÁT HIỆN VĂNG] {acc['name']} ({pkg}){C_RESET}")
                        print(f"{C_RED}     ➔ Lý do: {reason} -> Đang tự động Rejoin lại Game {cfg['game_id']}...{C_RESET}")
                        launch_package_tab(pkg, cfg["game_id"], acc)
                        time.sleep(8)
                    else:
                        print(f"{C_GREEN}{C_BOLD}  [✔ ONLINE] {acc['name']:<18} | {pkg} -> Đang trong Game ổn định{C_RESET}")
                else:
                    if not pid:
                        print(f"{C_RED}{C_BOLD}  [⚠ TẮT APP] {pkg} -> Đang mở lại & Join Game {cfg['game_id']}...{C_RESET}")
                        launch_package_tab(pkg, cfg["game_id"], None)
                        time.sleep(8)
                    else:
                        print(f"{C_GREEN}{C_BOLD}  [✔ RUNNING] {pkg} (PID: {pid}) -> App đang chạy ổn định{C_RESET}")
            
            time.sleep(cfg.get("delay", 20))
    except KeyboardInterrupt:
        print(f"\n{C_YELLOW}{C_BOLD}  [!] Đã dừng chế độ Auto-Rejoin.{C_RESET}")
        time.sleep(1.5)

while True:
    os.system("clear")
    cfg = load_cfg()
    pkgs_list = cfg.get("packages", [])
    active_count = sum(1 for p in pkgs_list if p.get("active", True))
    cpu_usage, ram_usage = get_system_stats()
