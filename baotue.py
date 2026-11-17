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

def scan_packages():
    found = set()
    # Cách 1: Quét trực tiếp các ứng dụng nhận giao thức roblox:// (Nhận diện mọi bản mod/clone kể cả đổi tên lạ)
    q_out = os.popen('cmd package query-activities -a android.intent.action.VIEW -d "roblox://" 2>/dev/null').read()
    for line in q_out.splitlines():
        line = line.strip()
        if line.startswith("packageName="):
            pkg = line.split("=", 1)[1].strip()
            if pkg:
                found.add(pkg)

    # Cách 2: Quét bổ sung theo danh sách từ khóa các client phổ biến
    keywords = ["roblox", "delta", "arceus", "codex", "fluxus", "hydrogen", "vega", "trigon", "evon"]
    all_pkgs = os.popen("pm list packages -3").read().splitlines()
    for line in all_pkgs:
        pkg = line.replace("package:", "").strip()
        if any(k in pkg.lower() for k in keywords):
            found.add(pkg)

    return sorted(list(found))

def verify_cookie(cookie):
    try:
        r = requests.get(
            "https://users.roblox.com/v1/users/authenticated",
            cookies={".ROBLOSECURITY": cookie},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            return str(data["id"]), data["name"]
    except Exception:
        pass
    return None, None

def is_in_game(user_id):
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
    try:
        s = requests.Session()
        s.cookies[".ROBLOSECURITY"] = cookie
        headers = {"Referer": "https://www.roblox.com/"}
        r1 = s.post("https://auth.roblox.com/v1/authentication-ticket", headers=headers, timeout=10)
        headers["x-csrf-token"] = r1.headers.get("x-csrf-token", "")
        r2 = s.post("https://auth.roblox.com/v1/authentication-ticket", headers=headers, timeout=10)
        return r2.headers.get("rbx-authentication-ticket")
    except Exception:
        return None

def launch_tab(pkg, game_id, cookie, username):
    print(f"{C_YELLOW}  [⏳] Đang làm mới & khởi chạy cho: {C_BOLD}{username}{C_RESET} {C_DIM}({pkg}){C_RESET}")
    os.system(f"am force-stop {pkg}")
    time.sleep(2)
    ticket = get_auth_ticket(cookie)
    if not ticket:
        print(f"{C_RED}  [❌] Lỗi: Cookie của {username} đã hết hạn hoặc bị lỗi!{C_RESET}")
        return
    url = f"roblox://placeId={game_id}&ticket={ticket}"
    # Dùng -p {pkg} kết hợp ActivityProtocolLaunch để mở chuẩn trên mọi bản mod/clone
    os.system(f'am start -p {pkg} -a android.intent.action.VIEW -d "{url}" > /dev/null 2>&1')
    print(f"{C_GREEN}  [✔] Đã gửi lệnh vào Game ID {game_id} thành công!{C_RESET}")

def run_auto_rejoin(cfg):
    active_pkgs = [p["pkg"] for p in cfg.get("packages", []) if p.get("active", True)]
    run_accounts = [a for a in cfg["accounts"] if a["pkg"] in active_pkgs]

    if not run_accounts:
        print(f"\n{C_RED}  [!] Không có tài khoản nào đang được BẬT chạy trên CloudPhone!{C_RESET}")
        print(f"{C_YELLOW}  ➔ Hãy kiểm tra mục [2] (Bật Package) và mục [3] (Gắn Cookie).{C_RESET}")
        time.sleep(3)
        return
    
    os.system("clear")
    print(f"{C_CYAN}╔══════════════════════════════════════════════════════════════════╗{C_RESET}")
    print(f"{C_CYAN}║{C_BOLD}{C_PURPLE}              🚀 HỆ THỐNG AUTO-REJOIN CLOUDPHONE 🚀               {C_RESET}{C_CYAN}║{C_RESET}")
    print(f"{C_CYAN}╚══════════════════════════════════════════════════════════════════╝{C_RESET}")
    print(f"  {C_YELLOW}• Game ID Mục Tiêu   :{C_RESET} {C_BOLD}{cfg['game_id']}{C_RESET}")
    print(f"  {C_YELLOW}• Số Tab Đang Chạy   :{C_RESET} {C_BOLD}{len(run_accounts)} tab được chọn{C_RESET}")
    print(f"  {C_YELLOW}• Chu Kỳ Quét Lỗi    :{C_RESET} {C_BOLD}{cfg.get('delay', 20)} giây/lần{C_RESET}")
    print(f"{C_DIM}────────────────────────────────────────────────────────────────────{C_RESET}")

    print(f"{C_PURPLE}  [⚡] Đang khởi động đồng loạt các tab đã chọn...{C_RESET}")
    for acc in run_accounts:
        launch_tab(acc["pkg"], cfg["game_id"], acc["cookie"], acc["name"])
        time.sleep(6)

    print(f"\n{C_GREEN}{C_BOLD}  [✔] HỆ THỐNG GIÁM SÁT ĐÃ KÍCH HOẠT! (Nhấn Ctrl + C để dừng){C_RESET}\n")
    
    try:
        while True:
            print(f"{C_DIM}────────────────────────────────────────────────────────────────────{C_RESET}")
            print(f"{C_CYAN}  [⏰ Quét lúc: {time.strftime('%H:%M:%S')}]{C_RESET}")
            for acc in run_accounts:
                pid = os.popen(f"pidof {acc['pkg']}").read().strip()
                ingame = is_in_game(acc["uid"])
                
                if not pid or not ingame:
                    reason = "Tắt ứng dụng" if not pid else "Mất kết nối / Văng sảnh"
                    print(f"{C_RED}  [⚠ VĂNG] {acc['name']} -> Lý do: {reason}! Đang Rejoin...{C_RESET}")
                    launch_tab(acc["pkg"], cfg["game_id"], acc["cookie"], acc["name"])
                    time.sleep(8)
                else:
                    print(f"{C_GREEN}  [✔ ONLINE] {acc['name']:<18} | {C_DIM}{acc['pkg']}{C_RESET} -> Đang cày ổn định")
            
            time.sleep(cfg.get("delay", 20))
    except KeyboardInterrupt:
        print(f"\n{C_YELLOW}  [!] Đã dừng chế độ Auto-Rejoin.{C_RESET}")
        time.sleep(1.5)

while True:
    os.system("clear")
    cfg = load_cfg()
    pkgs_list = cfg.get("packages", [])
    active_count = sum(1 for p in pkgs_list if p.get("active", True))
    
    print(f"{C_CYAN}╔══════════════════════════════════════════════════════════════════╗{C_RESET}")
    print(f"{C_CYAN}║{C_BOLD}{C_PURPLE}                 ⚡ BAOTUE REJOIN PRO - CLOUDPHONE ⚡               {C_RESET}{C_CYAN}║{C_RESET}")
    print(f"{C_CYAN}║{C_DIM}           Hệ Thống Tự Động Treo Game & Quản Lý Đa Tài Khoản      {C_RESET}{C_CYAN}║{C_RESET}")
    print(f"{C_CYAN}╠══════════════════════════════════════════════════════════════════╣{C_RESET}")
    print(f"{C_CYAN}║{C_RESET}  {C_YELLOW}• Game ID Mục Tiêu   :{C_RESET} {C_BOLD}{cfg['game_id']:<41}{C_RESET}{C_CYAN}║{C_RESET}")
    print(f"{C_CYAN}║{C_RESET}  {C_YELLOW}• Thời Gian Quét     :{C_RESET} {C_BOLD}{str(cfg.get('delay', 20)) + ' giây / vòng':<41}{C_RESET}{C_CYAN}║{C_RESET}")
    print(f"{C_CYAN}║{C_RESET}  {C_YELLOW}• Package CloudPhone :{C_RESET} {C_BOLD}{f'{active_count} đang BẬT / {len(pkgs_list)} đã lưu':<41}{C_RESET}{C_CYAN}║{C_RESET}")
    print(f"{C_CYAN}║{C_RESET}  {C_YELLOW}• Tài Khoản Cookie   :{C_RESET} {C_BOLD}{str(len(cfg['accounts'])) + ' tài khoản đã gắn':<41}{C_RESET}{C_CYAN}║{C_RESET}")
    print(f"{C_CYAN}╚══════════════════════════════════════════════════════════════════╝{C_RESET}")
    
    print(f"\n{C_BOLD}{C_CYAN}   ══════════════════════[ BẢNG ĐIỀU KHIỂN ]══════════════════════{C_RESET}\n")
    print(f"     {C_GREEN}[1]{C_RESET}  🚀  {C_BOLD}Khởi động các tab đã chọn & Chạy Auto-Rejoin{C_RESET}")
    print(f"     {C_GREEN}[2]{C_RESET}  📦  {C_BOLD}Set Package & Chọn Package chạy trên CloudPhone{C_RESET}")
    print(f"     {C_GREEN}[3]{C_RESET}  🍪  {C_BOLD}Nhập Cookie & Gắn tài khoản vào Package{C_RESET}")
    print(f"     {C_GREEN}[4]{C_RESET}  ⚙️   {C_BOLD}Cài đặt ID Game & Thời gian quét (Delay){C_RESET}")
    print(f"     {C_GREEN}[5]{C_RESET}  🛑  {C_BOLD}Kill toàn bộ tab Roblox ngay lập tức{C_RESET}")
    print(f"     {C_GREEN}[6]{C_RESET}  📊  {C_BOLD}Kiểm tra trạng thái In-Game chi tiết từng tab{C_RESET}")
    print(f"     {C_GREEN}[7]{C_RESET}  🗑️   {C_BOLD}Xóa tài khoản hoặc Package khỏi danh sách{C_RESET}")
    print(f"     {C_RED}[0]{C_RESET}  🚪  {C_BOLD}Thoát chương trình{C_RESET}")
    print(f"\n{C_CYAN}   ════════════════════════════════════════════════════════════════{C_RESET}")
    
    choice = input(f"\n{C_YELLOW}   ➜ Nhập lựa chọn của bạn [0-7]: {C_RESET}").strip()

    if choice == "1":
        run_auto_rejoin(cfg)
        
    elif choice == "2":
        while True:
            os.system("clear")
            cfg = load_cfg()
            saved_pkgs = cfg.get("packages", [])
            print(f"{C_CYAN}╔══════════════════════════════════════════════════════════════════╗{C_RESET}")
            print(f"{C_CYAN}║{C_BOLD}          QUẢN LÝ & CHỌN PACKAGE CHẠY TRÊN CLOUDPHONE             {C_RESET}{C_CYAN}║{C_RESET}")
            print(f"{C_CYAN}╚══════════════════════════════════════════════════════════════════╝{C_RESET}")
            
            print(f"\n{C_PURPLE}{C_BOLD}  [DANH SÁCH PACKAGE ĐÃ LƯU - CHỌN ĐỂ BẬT/TẮT CHẠY]:{C_RESET}")
            if saved_pkgs:
                for i, item in enumerate(saved_pkgs):
                    status_tag = f"{C_GREEN}[✔ BẬT CHẠY]{C_RESET}" if item.get("active", True) else f"{C_RED}[✖ TẮT]     {C_RESET}"
                    print(f"    {C_YELLOW}[{i+1}]{C_RESET} {status_tag}  {C_BOLD}{item['pkg']}{C_RESET}")
            else:
                print(f"    {C_DIM}(Chưa có package nào trong danh sách){C_RESET}")

            print(f"\n{C_DIM}────────────────────────────────────────────────────────────────────{C_RESET}")
            print(f"  {C_GREEN}[A]{C_RESET} Quét tất cả Client (Delta, Arceus, Clone...) trên máy")
            print(f"  {C_GREEN}[D]{C_RESET} Hiển thị TOÀN BỘ ứng dụng đã cài trên máy (nếu quét tự động sót)")
            print(f"  {C_GREEN}[B]{C_RESET} Bật TẤT CẢ các Package đã lưu")
            print(f"  {C_GREEN}[C]{C_RESET} Tắt TẤT CẢ các Package đã lưu")
            print(f"  {C_YELLOW}[Số STT]{C_RESET} Nhập số thứ tự (vd: 1 hoặc 1,2) để Bật/Tắt nhanh")
            print(f"  {C_RED}[0]{C_RESET} Quay lại Menu chính")
            
            sub = input(f"\n{C_CYAN}  ➜ Nhập lựa chọn của bạn: {C_RESET}").strip()
            if sub == "0":
                break
            elif sub.upper() in ["A", "D"]:
                if sub.upper() == "A":
                    detected = scan_packages()
                else:
                    detected = sorted([p.replace("package:", "").strip() for p in os.popen("pm list packages -3").read().splitlines() if p.strip()])
                
                print(f"\n{C_GREEN}  [+] Tìm thấy {len(detected)} gói ứng dụng:{C_RESET}")
                for idx, p in enumerate(detected):
                    print(f"      {C_YELLOW}[{idx+1}]{C_RESET} {p}")
                inp = input(f"\n{C_CYAN}  ➔ Nhập STT muốn thêm (vd: 1,2,3 hoặc gõ 'all' hoặc nhập tên): {C_RESET}").strip()
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
                print(f"{C_GREEN}  [✔] Đã cập nhật danh sách Package!{C_RESET}")
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
        print(f"{C_CYAN}╔══════════════════════════════════════════════════════════════════╗{C_RESET}")
        print(f"{C_CYAN}║{C_BOLD}               NHẬP COOKIE & GẮN TÀI KHOẢN ROBLOX                 {C_RESET}{C_CYAN}║{C_RESET}")
        print(f"{C_CYAN}╚══════════════════════════════════════════════════════════════════╝{C_RESET}")
        saved_pkgs = cfg.get("packages", [])
        if not saved_pkgs:
            print(f"\n{C_RED}  [!] Bạn chưa thêm Package nào! Vui lòng vào mục [2] trước.{C_RESET}")
            input(f"\n{C_DIM}  Bấm Enter để quay lại...{C_RESET}")
            continue
            
        print(f"\n{C_GREEN}  Chọn Package để gắn tài khoản này:{C_RESET}")
        for i, item in enumerate(saved_pkgs):
            acc_match = next((a["name"] for a in cfg["accounts"] if a["pkg"] == item["pkg"]), "Chưa gắn nick")
            print(f"    {C_YELLOW}[{i+1}]{C_RESET} {item['pkg']:<28} {C_DIM}(Hiện tại: {acc_match}){C_RESET}")
            
        pkg_sel = input(f"\n{C_CYAN}  ➔ Chọn số thứ tự package: {C_RESET}").strip()
        if pkg_sel.isdigit() and 1 <= int(pkg_sel) <= len(saved_pkgs):
            target_pkg = saved_pkgs[int(pkg_sel)-1]["pkg"]
        else:
            print(f"{C_RED}  [!] Lựa chọn không hợp lệ!{C_RESET}")
            time.sleep(1.5)
            continue
            
        ck = input(f"{C_CYAN}  ➔ Dán chuỗi Cookie (.ROBLOSECURITY): {C_RESET}").strip()
        print(f"{C_YELLOW}  [⏳] Đang xác thực Cookie với máy chủ Roblox...{C_RESET}")
        uid, uname = verify_cookie(ck)
        
        if uid:
            cfg["accounts"] = [a for a in cfg["accounts"] if a["pkg"] != target_pkg]
            cfg["accounts"].append({"name": uname, "uid": uid, "pkg": target_pkg, "cookie": ck})
            save_cfg(cfg)
            print(f"\n{C_GREEN}  [✔ THÀNH CÔNG] Đã gắn nick {C_PURPLE}{uname}{C_GREEN} (ID: {uid}) vào {target_pkg}!{C_RESET}")
        else:
            print(f"\n{C_RED}  [❌ LỖI] Cookie không hợp lệ hoặc đã chết!{C_RESET}")
        input(f"\n{C_DIM}  Bấm Enter để quay lại menu...{C_RESET}")
        
    elif choice == "4":
        os.system("clear")
        print(f"{C_CYAN}╔══════════════════════════════════════════════════════════════════╗{C_RESET}")
        print(f"{C_CYAN}║{C_BOLD}                  CÀI ĐẶT THÔNG SỐ HỆ THỐNG                      {C_RESET}{C_CYAN}║{C_RESET}")
        print(f"{C_CYAN}╚══════════════════════════════════════════════════════════════════╝{C_RESET}")
        gid = input(f"\n{C_YELLOW}  ➔ Nhập ID Game mới (Enter giữ nguyên [{cfg['game_id']}]): {C_RESET}").strip()
        dl = input(f"{C_YELLOW}  ➔ Nhập Delay giây (Enter giữ nguyên [{cfg.get('delay', 20)}]s): {C_RESET}").strip()
        if gid: cfg["game_id"] = gid
        if dl.isdigit(): cfg["delay"] = int(dl)
        save_cfg(cfg)
        print(f"\n{C_GREEN}  [✔] Đã cập nhật thành công!{C_RESET}")
        time.sleep(1.5)
        
    elif choice == "5":
        os.system("clear")
        print(f"{C_YELLOW}  [⏳] Đang ép dừng toàn bộ tab Roblox trên CloudPhone...{C_RESET}")
        for item in cfg.get("packages", []):
            os.system(f"am force-stop {item['pkg']}")
        print(f"{C_GREEN}  [✔] Đã đóng xong toàn bộ tab!{C_RESET}")
        input(f"\n{C_DIM}  Bấm Enter để quay lại...{C_RESET}")
        
    elif choice == "6":
        os.system("clear")
        print(f"{C_CYAN}╔══════════════════════════════════════════════════════════════════╗{C_RESET}")
        print(f"{C_CYAN}║{C_BOLD}             KIỂM TRA TRẠNG THÁI IN-GAME CHI TIẾT                 {C_RESET}{C_CYAN}║{C_RESET}")
        print(f"{C_CYAN}╚══════════════════════════════════════════════════════════════════╝{C_RESET}")
        if not cfg["accounts"]:
            print(f"\n{C_RED}  (Chưa có tài khoản nào được cấu hình){C_RESET}")
        for i, a in enumerate(cfg["accounts"]):
            pid = os.popen(f"pidof {a['pkg']}").read().strip()
            ig = is_in_game(a["uid"])
            pkg_obj = next((p for p in cfg.get("packages", []) if p["pkg"] == a["pkg"]), {"active": True})
            run_mode = f"{C_GREEN}BẬT{C_RESET}" if pkg_obj.get("active", True) else f"{C_RED}TẮT{C_RESET}"
            app_st = f"{C_GREEN}RUNNING (PID: {pid}){C_RESET}" if pid else f"{C_RED}CLOSED{C_RESET}"
            game_st = f"{C_GREEN}🎮 IN-GAME{C_RESET}" if ig else f"{C_RED}❌ DISCONNECTED{C_RESET}"
            print(f"\n  {C_PURPLE}{C_BOLD}[{i+1}] {a['name']}{C_RESET} (Chế độ CloudPhone: {run_mode})")
            print(f"      • Package    : {a['pkg']}")
            print(f"      • Ứng dụng   : {app_st}")
            print(f"      • Trạng thái : {game_st}")
            print(f"  {C_DIM}──────────────────────────────────────────────────────────────────{C_RESET}")
        input(f"\n{C_CYAN}  Bấm Enter để quay lại menu...{C_RESET}")
        
    elif choice == "7":
        os.system("clear")
        print(f"{C_CYAN}=== QUẢN LÝ / XÓA DỮ LIỆU ==={C_RESET}")
        print(f"  [1] Xóa tài khoản (Cookie)")
        print(f"  [2] Xóa Package đã lưu")
        sub = input(f"\n  Chọn mục muốn xóa [1-2]: ").strip()
        if sub == "1":
            for i, a in enumerate(cfg["accounts"]):
                print(f"    [{i+1}] {a['name']} ({a['pkg']})")
            x = input("  Nhập STT tài khoản muốn xóa (hoặc gõ 'all'): ").strip()
            if x.lower() == "all": cfg["accounts"] = []
            elif x.isdigit() and 1 <= int(x) <= len(cfg["accounts"]): cfg["accounts"].pop(int(x)-1)
        elif sub == "2":
            for i, p in enumerate(cfg.get("packages", [])):
                print(f"    [{i+1}] {p['pkg']}")
            x = input("  Nhập STT package muốn xóa (hoặc gõ 'all'): ").strip()
            if x.lower() == "all": cfg["packages"] = []
            elif x.isdigit() and 1 <= int(x) <= len(cfg.get("packages", [])): cfg["packages"].pop(int(x)-1)
        save_cfg(cfg)
        print(f"{C_GREEN}  [✔] Đã cập nhật lại dữ liệu!{C_RESET}")
        time.sleep(1.5)
        
    elif choice == "0":
        os.system("clear")
        print(f"{C_CYAN}Hẹn gặp lại bạn!{C_RESET}")
        break
