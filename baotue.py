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
            mem_free = int(lines[1].split()[1])
            mem_available = int(lines[2].split()[1]) if len(lines) > 2 else mem_free
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

    keywords = ["roblox", "delta", "arceus", "codex", "fluxus", "hydrogen", "vega", "trigon", "evon"]
    all_pkgs = os.popen("pm list packages -3").read().splitlines()
    for line in all_pkgs:
        pkg = line.replace("package:", "").strip()
        if any(k in pkg.lower() for k in keywords):
            found.add(pkg)

    return sorted(list(found))

def verify_cookie(cookie):
    try:
        # Làm sạch định dạng cookie nếu người dùng lỡ copy thừa dấu nháy hoặc tiền tố
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
        # Bước 1: Lấy CSRF token
        r1 = s.post("https://auth.roblox.com/v1/authentication-ticket", headers=headers, timeout=10)
        csrf = r1.headers.get("x-csrf-token")
        if csrf:
            headers["x-csrf-token"] = csrf
        
        # Bước 2: Lấy vé đăng nhập chuẩn
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
    
    os.system(f"am force-stop {pkg} 2>/dev/null || su -c 'am force-stop {pkg}'")
    time.sleep(2)
    
    if acc_info and acc_info.get("cookie"):
        ticket = get_auth_ticket(acc_info["cookie"])
        if ticket:
            url = f"roblox://placeId={game_id}&ticket={ticket}"
            os.system(f'am start -p {pkg} -a android.intent.action.VIEW -d "{url}" > /dev/null 2>&1')
            print(f"{C_GREEN}{C_BOLD}  [✔] ĐÃ GỬI VÉ COOKIE & JOIN GAME ID {game_id} THÀNH CÔNG!{C_RESET}")
            return
        else:
            print(f"{C_RED}  [⚠] Không lấy được Ticket từ Cookie! Đang mở trực tiếp App...{C_RESET}")

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
    print(f"      {C_GREEN}{C_BOLD}[3]{C_RESET}   🍪   {C_WHITE}{C_BOLD}NHẬP NHIỀU COOKIE HÀNG LOẠT & GẮN VÀO PACKAGE{C_RESET}\n")
    print(f"      {C_GREEN}{C_BOLD}[4]{C_RESET}   ⚙️    {C_WHITE}{C_BOLD}CÀI ĐẶT ID GAME & THỜI GIAN QUÉT (DELAY){C_RESET}\n")
    print(f"      {C_GREEN}{C_BOLD}[5]{C_RESET}   🛑   {C_WHITE}{C_BOLD}KILL TOÀN BỘ TAB ROBLOX NGAY LẬP TỨC{C_RESET}\n")
    print(f"      {C_GREEN}{C_BOLD}[6]{C_RESET}   📊   {C_WHITE}{C_BOLD}KIỂM TRA TRẠNG THÁI IN-GAME (THEO PACKAGE ĐÃ SET){C_RESET}\n")
    print(f"      {C_GREEN}{C_BOLD}[7]{C_RESET}   🗑️    {C_WHITE}{C_BOLD}XÓA TÀI KHOẢN HOẶC PACKAGE KHỎI DANH SÁCH{C_RESET}\n")
    print(f"      {C_RED}{C_BOLD}[0]{C_RESET}   🚪   {C_RED}{C_BOLD}THOÁT CHƯƠNG TRÌNH{C_RESET}\n")
    print(f"{C_CYAN}{C_BOLD}   ════════════════════════════════════════════════════════════════════════════{C_RESET}")
    
    choice = input(f"\n{C_YELLOW}{C_BOLD}   ➜ NHẬP LỰA CHỌN CỦA BẠN [0-7]: {C_RESET}").strip()

    if choice == "1":
        run_auto_rejoin(cfg)
        
    elif choice == "2":
        while True:
            os.system("clear")
            cfg = load_cfg()
            saved_pkgs = cfg.get("packages", [])
            acc_map = {a["pkg"]: a["name"] for a in cfg.get("accounts", [])}
            
            print(f"{C_CYAN}{C_BOLD}╔════════════════════════════════════════════════════════════════════════════╗{C_RESET}")
            print(f"{C_CYAN}{C_BOLD}║              QUẢN LÝ & CHỌN PACKAGE CHẠY TRÊN CLOUDPHONE                   ║{C_RESET}")
            print(f"{C_CYAN}{C_BOLD}╚════════════════════════════════════════════════════════════════════════════╝{C_RESET}\n")
            
            print(f"{C_PURPLE}{C_BOLD}  [DANH SÁCH PACKAGE ĐÃ LƯU - BẬT/TẮT ĐỂ CHẠY]:{C_RESET}\n")
            if saved_pkgs:
                for i, item in enumerate(saved_pkgs):
                    status_tag = f"{C_GREEN}{C_BOLD}[✔ BẬT CHẠY]{C_RESET}" if item.get("active", True) else f"{C_RED}{C_BOLD}[✖ TẮT]     {C_RESET}"
                    linked_acc = f"{C_CYAN}(Nick: {acc_map[item['pkg']]}){C_RESET}" if item['pkg'] in acc_map else f"{C_DIM}(Chưa gắn Cookie){C_RESET}"
                    print(f"     {C_YELLOW}{C_BOLD}[{i+1}]{C_RESET}  {status_tag}  {C_WHITE}{C_BOLD}{item['pkg']:<28}{C_RESET} {linked_acc}\n")
            else:
                print(f"     {C_RED}(Chưa có package nào - Hãy bấm phím A để quét){C_RESET}\n")

            print(f"{C_CYAN}──────────────────────────────────────────────────────────────────────────────{C_RESET}\n")
            print(f"     {C_GREEN}{C_BOLD}[A]{C_RESET}  Quét tất cả Client (Delta, Arceus, Clone...) trên máy\n")
            print(f"     {C_GREEN}{C_BOLD}[D]{C_RESET}  Hiển thị TOÀN BỘ ứng dụng trên máy\n")
            print(f"     {C_GREEN}{C_BOLD}[B]{C_RESET}  Bật TẤT CẢ Package      |      {C_RED}{C_BOLD}[C]{C_RESET}  Tắt TẤT CẢ Package\n")
            print(f"     {C_YELLOW}{C_BOLD}[Số STT]{C_RESET}  Nhập số (vd: 1 hoặc 1,2) để Bật/Tắt nhanh      |      {C_RED}{C_BOLD}[0]{C_RESET}  Quay lại\n")
            
            sub = input(f"\n{C_CYAN}{C_BOLD}  ➜ NHẬP LỰA CHỌN CỦA BẠN: {C_RESET}").strip()
            if sub == "0":
                break
            elif sub.upper() in ["A", "D"]:
                detected = scan_packages() if sub.upper() == "A" else sorted([p.replace("package:", "").strip() for p in os.popen("pm list packages -3").read().splitlines() if p.strip()])
                
                print(f"\n{C_GREEN}{C_BOLD}  [+] TÌM THẤY {len(detected)} GÓI ỨNG DỤNG:{C_RESET}\n")
                for idx, p in enumerate(detected):
                    print(f"      {C_YELLOW}{C_BOLD}[{idx+1}]{C_RESET}  {C_WHITE}{C_BOLD}{p}{C_RESET}")
                inp = input(f"\n{C_CYAN}{C_BOLD}  ➔ Nhập STT muốn thêm (vd: 1,2,3 hoặc 'all'): {C_RESET}").strip()
                existing_names = [x["pkg"] for x in saved_pkgs]
                
                if inp.lower() == "all":
                    for p in detected:
                        if p not in existing_names:
                            saved_pkgs.append({"pkg": p, "active": True})
                else:
                    parts = [x.strip() for x in inp.split(",") if x.strip()]
                    for part in parts:
                        if part.isdigit() and 1 <= int(part) <= len(detected):
                            p_name = detected[int(part)-1]
                            if p_name not in existing_names:
                                saved_pkgs.append({"pkg": p_name, "active": True})
                                existing_names.append(p_name)
                        elif part and part not in existing_names:
                            saved_pkgs.append({"pkg": part, "active": True})
                            existing_names.append(part)
                cfg["packages"] = saved_pkgs
                save_cfg(cfg)
                print(f"\n{C_GREEN}{C_BOLD}  [✔] ĐÃ CẬP NHẬT DANH SÁCH PACKAGE!{C_RESET}")
                time.sleep(1.2)
            elif sub.upper() == "B":
                for item in saved_pkgs: item["active"] = True
                save_cfg(cfg)
            elif sub.upper() == "C":
                for item in saved_pkgs: item["active"] = False
                save_cfg(cfg)
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
        print(f"{C_CYAN}{C_BOLD}╔════════════════════════════════════════════════════════════════════════════╗{C_RESET}")
        print(f"{C_CYAN}{C_BOLD}║              NHẬP NHIỀU COOKIE HÀNG LOẠT VÀO CÁC PACKAGE                   ║{C_RESET}")
        print(f"{C_CYAN}{C_BOLD}╚════════════════════════════════════════════════════════════════════════════╝{C_RESET}\n")
        saved_pkgs = cfg.get("packages", [])
        if not saved_pkgs:
            print(f"{C_RED}{C_BOLD}  [!] Bạn chưa thêm Package nào! Vui lòng vào mục [2] trước.{C_RESET}")
            input(f"\n{C_DIM}  Bấm Enter để quay lại...{C_RESET}")
            continue
            
        print(f"{C_GREEN}{C_BOLD}  DANH SÁCH PACKAGE HIỆN CÓ TRÊN MÁY:{C_RESET}\n")
        for i, item in enumerate(saved_pkgs):
            acc_match = next((a["name"] for a in cfg["accounts"] if a["pkg"] == item["pkg"]), "Chưa gắn nick")
            print(f"     {C_YELLOW}{C_BOLD}[{i+1}]{C_RESET}  {C_WHITE}{C_BOLD}{item['pkg']:<30}{C_RESET} {C_PURPLE}(Hiện tại: {acc_match}){C_RESET}\n")
            
        print(f"{C_CYAN}──────────────────────────────────────────────────────────────────────────────{C_RESET}")
        print(f"  {C_YELLOW}HƯỚNG DẪN NHẬP HÀNG LOẠT:{C_RESET}")
        print(f"  Bạn có thể dán danh sách nhiều Cookie (mỗi dòng 1 cookie).")
        print(f"  Tool sẽ tự động ghép lần lượt các Cookie vào danh sách Package theo thứ tự từ trên xuống dưới.\n")
        
        print(f"{C_CYAN}{C_BOLD}  ➔ Dán danh sách Cookie vào bên dưới (Nhấn Enter 2 lần hoặc gõ 'END' ở dòng cuối để kết thúc):{C_RESET}")
        
        lines = []
        while True:
            try:
                line = input()
                if line.strip().upper() == "END":
                    break
                if not line.strip():
                    break
                lines.append(line.strip())
            except EOFError:
                break
                
        # Lọc ra các chuỗi có chứa định dạng cookie hoặc dài
        raw_cookies = []
        for l in lines:
            if "_|WARNING" in l or ".ROBLOSECURITY" in l or len(l) > 50:
                raw_cookies.append(l)

        if not raw_cookies:
            # Nếu nhập theo kiểu dán chung 1 dòng hoặc cách nhau
            raw_cookies = [c.strip() for c in "".join(lines).split() if len(c) > 50]

        print(f"\n{C_YELLOW}  [⏳] Đang xử lý và xác thực {len(raw_cookies)} Cookie với Roblox...{C_RESET}")
        
        success_count = 0
        for idx, raw_ck in enumerate(raw_cookies):
            if idx >= len(saved_pkgs):
                print(f"{C_RED}  [!] Số lượng cookie nhiều hơn số lượng Package hiện có! Bỏ qua các cookie thừa.{C_RESET}")
                break
            target_pkg = saved_pkgs[idx]["pkg"]
            uid, uname, valid_ck = verify_cookie(raw_ck)
            if uid:
                cfg["accounts"] = [a for a in cfg["accounts"] if a["pkg"] != target_pkg]
                cfg["accounts"].append({"name": uname, "uid": uid, "pkg": target_pkg, "cookie": valid_ck})
                print(f"  {C_GREEN}[✔] Gắn thành công: {C_PURPLE}{uname}{C_GREEN} ➔ {target_pkg}{C_RESET}")
                success_count += 1
            else:
                print(f"  {C_RED}[✖] Cookie thứ {idx+1} không hợp lệ hoặc đã chết, bỏ qua.{C_RESET}")
                
        save_cfg(cfg)
        print(f"\n{C_GREEN}{C_BOLD}  [✔ HOÀN TẤT] Đã gán thành công {success_count} tài khoản vào các Package!{C_RESET}")
        input(f"\n{C_DIM}  Bấm Enter để quay lại Menu chính...{C_RESET}")
        
    elif choice == "4":
        os.system("clear")
        print(f"{C_CYAN}{C_BOLD}╔════════════════════════════════════════════════════════════════════════════╗{C_RESET}")
        print(f"{C_CYAN}{C_BOLD}║                        CÀI ĐẶT THÔNG SỐ HỆ THỐNG                           ║{C_RESET}")
        print(f"{C_CYAN}{C_BOLD}╚════════════════════════════════════════════════════════════════════════════╝{C_RESET}\n")
        gid = input(f"{C_YELLOW}{C_BOLD}  ➔ Nhập ID Game mới (Enter giữ nguyên [{cfg['game_id']}]): {C_RESET}").strip()
        dl = input(f"\n{C_YELLOW}{C_BOLD}  ➔ Nhập Delay giây (Enter giữ nguyên [{cfg.get('delay', 20)}]s): {C_RESET}").strip()
        if gid: cfg["game_id"] = gid
        if dl.isdigit(): cfg["delay"] = int(dl)
        save_cfg(cfg)
        print(f"\n{C_GREEN}{C_BOLD}  [✔] ĐÃ CẬP NHẬT CẤU HÌNH THÀNH CÔNG!{C_RESET}")
        time.sleep(1.5)
        
    elif choice == "5":
        os.system("clear")
        print(f"{C_YELLOW}{C_BOLD}  [⏳] Đang ép dừng toàn bộ tab Roblox đã set...{C_RESET}")
        for item in cfg.get("packages", []):
            os.system(f"am force-stop {item['pkg']} 2>/dev/null || su -c 'am force-stop {item['pkg']}'")
        print(f"\n{C_GREEN}{C_BOLD}  [✔] ĐÃ ĐÓNG XONG TOÀN BỘ TAB!{C_RESET}")
        input(f"\n{C_DIM}  Bấm Enter để quay lại...{C_RESET}")
        
    elif choice == "6":
        os.system("clear")
        print(f"{C_CYAN}{C_BOLD}╔════════════════════════════════════════════════════════════════════════════╗{C_RESET}")
        print(f"{C_CYAN}{C_BOLD}║            KIỂM TRA TRẠNG THÁI IN-GAME (LIÊN KẾT SET PACKAGE)              ║{C_RESET}")
        print(f"{C_CYAN}{C_BOLD}╚════════════════════════════════════════════════════════════════════════════╝{C_RESET}\n")
        
        saved_pkgs = cfg.get("packages", [])
        acc_map = {a["pkg"]: a for a in cfg.get("accounts", [])}
        
        if not saved_pkgs:
            print(f"{C_RED}{C_BOLD}  (Chưa có Package nào được thêm ở mục [2]){C_RESET}\n")
        else:
            print(f"  {C_YELLOW}{C_BOLD}• ID Game đang cấu hình :{C_RESET} {C_GREEN}{C_BOLD}{cfg['game_id']}{C_RESET}\n")
            print(f"{C_CYAN}──────────────────────────────────────────────────────────────────────────────{C_RESET}")
            for i, item in enumerate(saved_pkgs):
                pkg = item["pkg"]
                is_active = item.get("active", True)
                acc = acc_map.get(pkg)
                pid = os.popen(f"pidof {pkg}").read().strip()
                
                mode_str = f"{C_GREEN}{C_BOLD}✔ BẬT CHẠY{C_RESET}" if is_active else f"{C_RED}{C_BOLD}✖ ĐANG TẮT{C_RESET}"
                app_str = f"{C_GREEN}{C_BOLD}ĐANG MỞ (PID: {pid}){C_RESET}" if pid else f"{C_RED}{C_BOLD}ĐÃ ĐÓNG (OFFLINE){C_RESET}"
                
                if acc:
                    ig = is_in_game(acc["uid"])
                    acc_str = f"{C_PURPLE}{C_BOLD}{acc['name']}{C_RESET} (ID: {acc['uid']})"
                    game_str = f"{C_GREEN}{C_BOLD}🎮 ĐANG TRONG GAME (IN-GAME){C_RESET}" if ig else f"{C_RED}{C_BOLD}❌ MẤT KẾT NỐI / NGOÀI SẢNH{C_RESET}"
                else:
                    acc_str = f"{C_DIM}Chưa gắn Cookie (Chạy theo App){C_RESET}"
                    game_str = f"{C_YELLOW}{C_BOLD}⚠ Không check được API (Chưa gắn Cookie){C_RESET}"

                print(f"\n  {C_YELLOW}{C_BOLD}[{i+1}] PACKAGE: {C_WHITE}{pkg}{C_RESET}")
                print(f"      • Chế độ CloudPhone : {mode_str}")
                print(f"      • Tài khoản gắn     : {acc_str}")
                print(f"      • Tiến trình App    : {app_str}")
                print(f"      • Trạng thái Game   : {game_str}\n")
                print(f"{C_DIM}──────────────────────────────────────────────────────────────────────────────{C_RESET}")
                
        input(f"\n{C_CYAN}{C_BOLD}  Bấm Enter để quay lại Menu chính...{C_RESET}")
        
    elif choice == "7":
        os.system("clear")
        print(f"{C_CYAN}{C_BOLD}=== QUẢN LÝ / XÓA DỮ LIỆU ==={C_RESET}\n")
        print(f"  {C_YELLOW}[1]{C_RESET} Xóa tài khoản (Cookie)\n")
        print(f"  {C_YELLOW}[2]{C_RESET} Xóa Package đã lưu\n")
        sub = input(f"  Chọn mục muốn xóa [1-2]: ").strip()
        if sub == "1":
            for i, a in enumerate(cfg["accounts"]):
                print(f"    [{i+1}] {a['name']} ({a['pkg']})")
            x = input("\n  Nhập STT tài khoản muốn xóa (hoặc gõ 'all'): ").strip()
            if x.lower() == "all": cfg["accounts"] = []
            elif x.isdigit() and 1 <= int(x) <= len(cfg["accounts"]): cfg["accounts"].pop(int(x)-1)
        elif sub == "2":
            for i, p in enumerate(cfg.get("packages", [])):
                print(f"    [{i+1}] {p['pkg']}")
            x = input("\n  Nhập STT package muốn xóa (hoặc gõ 'all'): ").strip()
            if x.lower() == "all": cfg["packages"] = []
            elif x.isdigit() and 1 <= int(x) <= len(cfg.get("packages", [])): cfg["packages"].pop(int(x)-1)
        save_cfg(cfg)
        print(f"\n{C_GREEN}{C_BOLD}  [✔] Đã cập nhật lại dữ liệu!{C_RESET}")
        time.sleep(1.5)
        
    elif choice == "0":
        os.system("clear")
        print(f"{C_CYAN}{C_BOLD}Hẹn gặp lại bạn!{C_RESET}")
        break
