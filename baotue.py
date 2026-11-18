import os
import time
import json
import requests

CFG_PATH = "/sdcard/Download/baotue_config.json"
EXPORT_DIR = "/sdcard/Download/"

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

def extract_cookie_from_pkg(pkg):
    """Cơ chế trích xuất siêu sâu 4 tầng qua quyền root trên VMOS"""
    try:
        # Tầng 1: Dùng lệnh find kết hợp strings quét toàn bộ các tệp trong thư mục /data/data/[pkg]/
        cmd1 = f"su -c 'find /data/data/{pkg}/ -type f 2>/dev/null | xargs strings 2>/dev/null | grep \"_|WARNING\"'"
        out1 = os.popen(cmd1).read().strip()
        if out1:
            for line in out1.splitlines():
                if len(line.strip()) > 50:
                    return line.strip().strip('"').strip("'")

        # Tầng 2: Quét trực tiếp trong thư mục databases và shared_prefs bằng bộ lọc nhị phân
        cmd2 = f"su -c 'grep -rho \"_|WARNING[^\"]*\" /data/data/{pkg}/databases/ /data/data/{pkg}/shared_prefs/ 2>/dev/null'"
        out2 = os.popen(cmd2).read().strip()
        if out2:
            for line in out2.splitlines():
                if len(line.strip()) > 50:
                    return line.strip().strip('"').strip("'")

        # Tầng 3: Quét trong thư mục app_webview (nơi lưu trữ cookie của trình duyệt nhúng)
        cmd3 = f"su -c 'find /data/data/{pkg}/app_webview/ -type f 2>/dev/null | xargs strings 2>/dev/null | grep -E \"(_|WARNING|ROBLOSECURITY)\"'"
        out3 = os.popen(cmd3).read().strip()
        if out3:
            for line in out3.splitlines():
                if len(line.strip()) > 50 and "_" in line:
                    clean = line.strip().strip('"').strip("'")
                    if "_|WARNING" in clean:
                        return clean
                    return clean

    except Exception:
        pass
    return None

def export_cookies_to_zarchiver(accounts):
    try:
        os.makedirs(EXPORT_DIR, exist_ok=True)
        file_path = os.path.join(EXPORT_DIR, "baotue_cookies.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("# === BAOTUE REJOIN PRO - EXPORTED COOKIES ===\n")
            for acc in accounts:
                f.write(f"# Name: {acc['name']} | ID: {acc['uid']} | Package: {acc['pkg']}\n")
                f.write(f"{acc['cookie']}\n\n")
        print(f"{C_GREEN}{C_BOLD}  [✔] Đã xuất file cookie tại: {file_path}{C_RESET}")
        print(f"{C_YELLOW}  ➔ Mở Zarchiver vào mục Download để xem file 'baotue_cookies.txt'.{C_RESET}")
    except Exception as e:
        print(f"{C_RED}  [!] Lỗi xuất file: {e}{C_RESET}")

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
    print(f"\n{C_YELLOW}{C_BOLD}  [⏳] ĐANG KÍCH HOẠT VÀ ĐĂNG NHẬP CHO TAB: {pkg}{C_RESET}")
    print(f"       {C_WHITE}• Tài khoản : {C_PURPLE}{display_name}{C_RESET}")
    print(f"       {C_WHITE}• Join Game : {C_CYAN}{game_id}{C_RESET}")
    
    os.system(f"am force-stop {pkg} 2>/dev/null || su -c 'am force-stop {pkg}'")
    time.sleep(2)
    
    if acc_info and acc_info.get("cookie"):
        cookie = acc_info["cookie"]
        ticket = get_auth_ticket(cookie)
        
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
            url = f"roblox://placeId={game_id}&ticket={ticket}"
            os.system(f'am start -p {pkg} -a android.intent.action.VIEW -d "{url}" > /dev/null 2>&1')
            print(f"{C_GREEN}{C_BOLD}  [✔] ĐÃ BƠM COOKIE & LOGIN THÀNH CÔNG VÀO GAME ID {game_id}!{C_RESET}")
            return

    url_direct = f"roblox://placeId={game_id}"
    os.system(f'am start -p {pkg} -a android.intent.action.VIEW -d "{url_direct}" > /dev/null 2>&1')
    print(f"{C_GREEN}{C_BOLD}  [✔] ĐÃ MỞ APP & JOIN THẲNG VÀO GAME ID {game_id}!{C_RESET}")

def run_auto_rejoin(cfg):
    active_pkgs = [p["pkg"] for p in cfg.get("packages", []) if p.get("active", True)]
    if not active_pkgs:
        print(f"\n{C_RED}{C_BOLD}  [!] BẠN CHƯA CHỌN PACKAGE NÀO ĐỂ CHẠY!{C_RESET}")
        time.sleep(3)
        return

    acc_map = {a["pkg"]: a for a in cfg.get("accounts", [])}
    os.system("clear")
    print(f"{C_CYAN}{C_BOLD}╔════════════════════════════════════════════════════════════════════════════╗{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}║                 🚀 HỆ THỐNG AUTO-REJOIN ĐANG HOẠT ĐỘNG 🚀                  ║{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}╚════════════════════════════════════════════════════════════════════════════╝{C_RESET}\n")

    for pkg in active_pkgs:
        launch_package_tab(pkg, cfg["game_id"], acc_map.get(pkg))
        time.sleep(6)

    print(f"\n{C_GREEN}{C_BOLD}  [⚡] GIÁM SÁT TỰ ĐỘNG ĐÃ KÍCH HOẠT! (Nhấn Ctrl + C để dừng){C_RESET}\n")
    try:
        while True:
            for pkg in active_pkgs:
                acc = acc_map.get(pkg)
                pid = os.popen(f"pidof {pkg}").read().strip()
                if acc and acc.get("uid"):
                    ingame = is_in_game(acc["uid"])
                    if not pid or not ingame:
                        launch_package_tab(pkg, cfg["game_id"], acc)
                        time.sleep(8)
                else:
                    if not pid:
                        launch_package_tab(pkg, cfg["game_id"], None)
                        time.sleep(8)
            time.sleep(cfg.get("delay", 20))
    except KeyboardInterrupt:
        print(f"\n{C_YELLOW}{C_BOLD}  [!] Đã dừng Auto-Rejoin.{C_RESET}")
        time.sleep(1.5)

while True:
    os.system("clear")
    cfg = load_cfg()
    pkgs_list = cfg.get("packages", [])
    active_count = sum(1 for p in pkgs_list if p.get("active", True))
    cpu_usage, ram_usage = get_system_stats()
    
    print(f"{C_CYAN}{C_BOLD}╔════════════════════════════════════════════════════════════════════════════╗{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}║                                                                            ║{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}║               ⚡  BAOTUE REJOIN PRO - CLOUDPHONE EDITION  ⚡               ║{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}║                                                                            ║{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}╠════════════════════════════════════════════════════════════════════════════╣{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}║                                                                            ║{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}║{C_RESET}   {C_YELLOW}{C_BOLD}• ID GAME MỤC TIÊU     :{C_RESET}  {C_GREEN}{C_BOLD}{cfg['game_id']:<47}{C_RESET}{C_CYAN}{C_BOLD}║{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}║{C_RESET}   {C_YELLOW}{C_BOLD}• HIỆU SUẤT THIẾT BỊ   :{C_RESET}  {C_PURPLE}{C_BOLD}{f'CPU: {cpu_usage}  |  RAM: {ram_usage}':<47}{C_RESET}{C_CYAN}{C_BOLD}║{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}║{C_RESET}   {C_YELLOW}{C_BOLD}• PACKAGE CLOUDPHONE   :{C_RESET}  {C_WHITE}{C_BOLD}{f'{active_count} đang BẬT  /  {len(pkgs_list)} đã lưu':<47}{C_RESET}{C_CYAN}{C_BOLD}║{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}║{C_RESET}   {C_YELLOW}{C_BOLD}• TÀI KHOẢN COOKIE     :{C_RESET}  {C_WHITE}{C_BOLD}{str(len(cfg['accounts'])) + ' tài khoản đã liên kết':<47}{C_RESET}{C_CYAN}{C_BOLD}║{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}║                                                                            ║{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}╚════════════════════════════════════════════════════════════════════════════╝{C_RESET}")
    
    print(f"\n{C_CYAN}{C_BOLD}   ══════════════════════════[ BẢNG ĐIỀU KHIỂN CHÍNH ]══════════════════════════{C_RESET}\n")
    print(f"      {C_GREEN}{C_BOLD}[1]{C_RESET}   🚀   {C_WHITE}{C_BOLD}KHỞI ĐỘNG TẤT CẢ TAB ĐÃ SET & CHẠY AUTO-REJOIN{C_RESET}\n")
    print(f"      {C_GREEN}{C_BOLD}[2]{C_RESET}   📦   {C_WHITE}{C_BOLD}SET PACKAGE & CHỌN PACKAGE CHẠY TRÊN CLOUDPHONE{C_RESET}\n")
    print(f"      {C_GREEN}{C_BOLD}[3]{C_RESET}   🍪   {C_WHITE}{C_BOLD}NHẬP NHIỀU COOKIE HÀNG LOẠT & TỰ ĐỘNG LOGIN{C_RESET}\n")
    print(f"      {C_GREEN}{C_BOLD}[8]{C_RESET}   📥   {C_WHITE}{C_BOLD}GET COOKIE SIÊU SÂU TỪ APP ĐÃ ĐĂNG NHẬP + XUẤT FILE ZARCHIVER{C_RESET}\n")
    print(f"      {C_GREEN}{C_BOLD}[4]{C_RESET}   ⚙️    {C_WHITE}{C_BOLD}CÀI ĐẶT ID GAME & THỜI GIAN QUÉT (DELAY){C_RESET}\n")
    print(f"      {C_GREEN}{C_BOLD}[5]{C_RESET}   🛑   {C_WHITE}{C_BOLD}KILL TOÀN BỘ TAB ROBLOX NGAY LẬP TỨC{C_RESET}\n")
    print(f"      {C_GREEN}{C_BOLD}[6]{C_RESET}   📊   {C_WHITE}{C_BOLD}KIỂM TRA TRẠNG THÁI IN-GAME (THEO PACKAGE ĐÃ SET){C_RESET}\n")
    print(f"      {C_GREEN}{C_BOLD}[7]{C_RESET}   🗑️    {C_WHITE}{C_BOLD}XÓA TÀI KHOẢN HOẶC PACKAGE KHỎI DANH SÁCH{C_RESET}\n")
    print(f"      {C_RED}{C_BOLD}[0]{C_RESET}   🚪   {C_RED}{C_BOLD}THOÁT CHƯƠNG TRÌNH{C_RESET}\n")
    print(f"{C_CYAN}{C_BOLD}   ════════════════════════════════════════════════════════════════════════════{C_RESET}")
    
    choice = input(f"\n{C_YELLOW}{C_BOLD}   ➜ NHẬP LỰA CHỌN CỦA BẠN [0-8]: {C_RESET}").strip()

    if choice == "1":
        run_auto_rejoin(cfg)
    elif choice == "2":
        while True:
            os.system("clear")
            cfg = load_cfg()
            saved_pkgs = cfg.get("packages", [])
            print(f"{C_CYAN}{C_BOLD}╔════════════════════════════════════════════════════════════════════════════╗{C_RESET}")
            print(f"{C_CYAN}{C_BOLD}║              QUẢN LÝ & CHỌN PACKAGE CHẠY TRÊN CLOUDPHONE                   ║{C_RESET}")
            print(f"{C_CYAN}{C_BOLD}╚════════════════════════════════════════════════════════════════════════════╝{C_RESET}\n")
            if saved_pkgs:
                for i, item in enumerate(saved_pkgs):
                    status_tag = f"{C_GREEN}{C_BOLD}[✔ BẬT CHẠY]{C_RESET}" if item.get("active", True) else f"{C_RED}{C_BOLD}[✖ TẮT]     {C_RESET}"
                    print(f"     {C_YELLOW}{C_BOLD}[{i+1}]{C_RESET}  {status_tag}  {C_WHITE}{C_BOLD}{item['pkg']}{C_RESET}\n")
            print(f"  {C_GREEN}[A]{C_RESET} Quét tất cả Client trên máy  |  {C_RED}[0]{C_RESET} Quay lại")
            sub = input(f"\n  ➜ Lựa chọn: ").strip()
            if sub == "0": break
            elif sub.upper() == "A":
                detected = scan_packages()
                for p in detected:
                    if p not in [x["pkg"] for x in saved_pkgs]:
                        saved_pkgs.append({"pkg": p, "active": True})
                cfg["packages"] = saved_pkgs
                save_cfg(cfg)
                print(f"{C_GREEN}  [✔] Đã cập nhật!{C_RESET}")
                time.sleep(1.2)
            else:
                parts = [x.strip() for x in sub.split(",") if x.strip().isdigit()]
                for part in parts:
                    idx = int(part) - 1
                    if 0 <= idx < len(saved_pkgs):
                        saved_pkgs[idx]["active"] = not saved_pkgs[idx].get("active", True)
                cfg["packages"] = saved_pkgs
                save_cfg(cfg)
    elif choice == "3":
        os.system("clear")
        print(f"{C_CYAN}=== NHẬP COOKIE HÀNG LOẠT ==={C_RESET}\n")
        saved_pkgs = cfg.get("packages", [])
        if not saved_pkgs:
            input("Chưa có Package! Bấm Enter...")
            continue
        print("Dán danh sách Cookie (Gõ 'END' ở dòng cuối):")
        lines = []
        while True:
            try:
                line = input()
                if line.strip().upper() == "END": break
                if not line.strip(): break
                lines.append(line.strip())
            except EOFError: break
        raw_cookies = [l for l in lines if len(l) > 50]
        for idx, raw_ck in enumerate(raw_cookies):
            if idx >= len(saved_pkgs): break
            target_pkg = saved_pkgs[idx]["pkg"]
            uid, uname, valid_ck = verify_cookie(raw_ck)
            if uid:
                cfg["accounts"] = [a for a in cfg["accounts"] if a["pkg"] != target_pkg]
                new_acc = {"name": uname, "uid": uid, "pkg": target_pkg, "cookie": valid_ck}
                cfg["accounts"].append(new_acc)
                save_cfg(cfg)
                launch_package_tab(target_pkg, cfg["game_id"], new_acc)
        export_cookies_to_zarchiver(cfg["accounts"])
        input("\nHoàn tất! Bấm Enter...")
    elif choice == "8":
        os.system("clear")
        print(f"{C_CYAN}{C_BOLD}╔════════════════════════════════════════════════════════════════════════════╗{C_RESET}")
        print(f"{C_CYAN}{C_BOLD}║           QUÉT SIÊU SÂU GET COOKIE TỪ APP ĐÃ ĐĂNG NHẬP SẴN                 ║{C_RESET}")
        print(f"{C_CYAN}{C_BOLD}╚════════════════════════════════════════════════════════════════════════════╝{C_RESET}\n")
        saved_pkgs = cfg.get("packages", [])
        if not saved_pkgs:
            print(f"{C_RED}  [!] Chưa có Package nào!{C_RESET}")
            input("\nBấm Enter...")
            continue
            
        extracted_count = 0
        for item in saved_pkgs:
            pkg = item["pkg"]
            print(f"  {C_YELLOW}• Đang quét siêu sâu bộ nhớ app: {pkg}...{C_RESET}")
            ck = extract_cookie_from_pkg(pkg)
            if ck:
                uid, uname, valid_ck = verify_cookie(ck)
                if uid:
                    cfg["accounts"] = [a for a in cfg["accounts"] if a["pkg"] != pkg]
                    cfg["accounts"].append({"name": uname, "uid": uid, "pkg": pkg, "cookie": valid_ck})
                    print(f"    {C_GREEN}[✔ LẤY THÀNH CÔNG] Nick: {C_PURPLE}{uname}{C_GREEN} (ID: {uid}) ➔ {pkg}{C_RESET}")
                    extracted_count += 1
                else:
                    print(f"    {C_RED}[✖] Tìm thấy chuỗi token nhưng không hợp lệ.{C_RESET}")
            else:
                print(f"    {C_RED}[✖] Không tìm thấy phiên đăng nhập trong app này.{C_RESET}")
                
        save_cfg(cfg)
        if extracted_count > 0:
            export_cookies_to_zarchiver(cfg["accounts"])
            
        print(f"\n{C_GREEN}{C_BOLD}  [✔ HOÀN TẤT] Trích xuất thành công {extracted_count} tài khoản!{C_RESET}")
        input(f"\n{C_DIM}  Bấm Enter để quay lại...{C_RESET}")
    elif choice == "4":
        gid = input("ID Game mới: ").strip()
        if gid: cfg["game_id"] = gid
        save_cfg(cfg)
    elif choice == "5":
        for item in cfg.get("packages", []):
            os.system(f"am force-stop {item['pkg']} 2>/dev/null || su -c 'am force-stop {item['pkg']}'")
        input("Đã kill xong! Bấm Enter...")
    elif choice == "6":
        os.system("clear")
        print("=== TRẠNG THÁI IN-GAME ===")
        for i, item in enumerate(cfg.get("packages", [])):
            pkg = item["pkg"]
            acc = next((a for a in cfg.get("accounts", []) if a["pkg"] == pkg), None)
            pid = os.popen(f"pidof {pkg}").read().strip()
            print(f"[{i+1}] {pkg} | App PID: {pid or 'OFF'} | Nick: {acc['name'] if acc else 'Chưa gắn'}")
        input("\nBấm Enter...")
    elif choice == "7":
        cfg["accounts"] = []
        cfg["packages"] = []
        save_cfg(cfg)
        input("Đã xóa sạch! Bấm Enter...")
    elif choice == "0":
        break
