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
C_BLUE = "\033[94m"
C_BOLD = "\033[1m"
C_DIM = "\033[2m"
C_RESET = "\033[0m"

def load_cfg():
    if os.path.exists(CFG_PATH):
        with open(CFG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"game_id": "2753915549", "delay": 20, "accounts": []}

def save_cfg(data):
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def scan_packages():
    out = os.popen("pm list packages | grep roblox").read().splitlines()
    return [p.replace("package:", "").strip() for p in out if p.strip()]

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
    print(f"{C_YELLOW}[⏳] Đang làm mới & khởi chạy cho: {C_BOLD}{username}{C_RESET} {C_DIM}({pkg}){C_RESET}")
    os.system(f"am force-stop {pkg}")
    time.sleep(2)
    ticket = get_auth_ticket(cookie)
    if not ticket:
        print(f"{C_RED}[❌] Lỗi: Cookie của {username} đã hết hạn hoặc không hợp lệ!{C_RESET}")
        return
    url = f"roblox://placeId={game_id}&ticket={ticket}"
    os.system(f'am start -n {pkg}/com.roblox.client.ActivityProtocolLaunch -a android.intent.action.VIEW -d "{url}" > /dev/null 2>&1')
    print(f"{C_GREEN}[✔] Đã gửi lệnh vào Game ID {game_id} thành công!{C_RESET}")

def run_auto_rejoin(cfg):
    if not cfg["accounts"]:
        print(f"\n{C_RED}[!] Danh sách tài khoản trống! Vui lòng thêm tài khoản ở mục [2].{C_RESET}")
        time.sleep(2)
        return
    
    os.system("clear")
    print(f"{C_CYAN}╔════════════════════════════════════════════╗{C_RESET}")
    print(f"{C_CYAN}║{C_BOLD}       HỆ THỐNG AUTO-REJOIN ĐANG CHẠY       {C_RESET}{C_CYAN}║{C_RESET}")
    print(f"{C_CYAN}╚════════════════════════════════════════════╝{C_RESET}")
    print(f"{C_YELLOW}[*] Game ID Mục tiêu : {C_BOLD}{cfg['game_id']}{C_RESET}")
    print(f"{C_YELLOW}[*] Thời gian quét   : {C_BOLD}{cfg.get('delay', 20)} giây/lần{C_RESET}")
    print(f"{C_DIM}--------------------------------------------{C_RESET}")

    print(f"{C_PURPLE}[🚀] Đang khởi động toàn bộ các tab lần đầu...{C_RESET}")
    for acc in cfg["accounts"]:
        launch_tab(acc["pkg"], cfg["game_id"], acc["cookie"], acc["name"])
        time.sleep(6)

    print(f"\n{C_GREEN}{C_BOLD}[⚡] ĐÃ KÍCH HOẠT CHẾ ĐỘ GIÁM SÁT TỰ ĐỘNG!{C_RESET}")
    print(f"{C_DIM}(Nhấn tổ hợp phím Ctrl + C trên bàn phím bất cứ lúc nào để dừng lại){C_RESET}\n")
    
    try:
        while True:
            print(f"{C_DIM}--------------------------------------------{C_RESET}")
            print(f"{C_CYAN}[⏰ Kiểm tra lúc: {time.strftime('%H:%M:%S')}]{C_RESET}")
            for acc in cfg["accounts"]:
                pid = os.popen(f"pidof {acc['pkg']}").read().strip()
                ingame = is_in_game(acc["uid"])
                
                if not pid or not ingame:
                    status_reason = "Mất tiến trình App" if not pid else "Bị văng khỏi Game (Sảnh/Disconnect)"
                    print(f"{C_RED}[⚠ PHÁT HIỆN VĂNG] {acc['name']} -> Lý do: {status_reason}! Đang Rejoin...{C_RESET}")
                    launch_tab(acc["pkg"], cfg["game_id"], acc["cookie"], acc["name"])
                    time.sleep(8)
                else:
                    print(f"{C_GREEN}[✔ ONLINE] {acc['name']} {C_DIM}({acc['pkg']}) -> Đang cày ổn định trong Game.{C_RESET}")
            
            time.sleep(cfg.get("delay", 20))
    except KeyboardInterrupt:
        print(f"\n{C_YELLOW}[!] Đã dừng chế độ Auto-Rejoin theo yêu cầu của bạn.{C_RESET}")
        time.sleep(1.5)

while True:
    os.system("clear")
    cfg = load_cfg()
    
    # --- GIAO DIỆN BANNER HOÀNH TRÁNG ---
    print(f"{C_CYAN}╔════════════════════════════════════════════════════╗{C_RESET}")
    print(f"{C_CYAN}║{C_BOLD}{C_PURPLE}             ⚡ BAOTUE REJOIN PRO V10 ⚡             {C_RESET}{C_CYAN}║{C_RESET}")
    print(f"{C_CYAN}║{C_DIM}        Hệ Thống Quản Lý & Tự Động Rejoin Roblox    {C_RESET}{C_CYAN}║{C_RESET}")
    print(f"{C_CYAN}╠════════════════════════════════════════════════════╣{C_RESET}")
    print(f"{C_CYAN}║{C_RESET} {C_YELLOW}Game ID Hiện Tại :{C_RESET} {C_BOLD}{cfg['game_id']:<26}{C_RESET}{C_CYAN}║{C_RESET}")
    print(f"{C_CYAN}║{C_RESET} {C_YELLOW}Thời Gian Delay  :{C_RESET} {C_BOLD}{str(cfg.get('delay', 20)) + ' giây':<26}{C_RESET}{C_CYAN}║{C_RESET}")
    print(f"{C_CYAN}║{C_RESET} {C_YELLOW}Tổng Số Tab Lưu  :{C_RESET} {C_BOLD}{str(len(cfg['accounts'])) + ' tài khoản':<26}{C_RESET}{C_CYAN}║{C_RESET}")
    print(f"{C_CYAN}╚════════════════════════════════════════════════════╝{C_RESET}")
    
    print(f"\n{C_BOLD}   CHỌN CHỨC NĂNG HỆ THỐNG:{C_RESET}")
    print(f"   {C_GREEN}[1]{C_RESET} 🚀 Khởi động tất cả tab & Chạy Auto-Rejoin")
    print(f"   {C_GREEN}[2]{C_RESET} 📥 Tự động quét Package & Thêm Cookie tài khoản")
    print(f"   {C_GREEN}[3]{C_RESET} ⚙️  Cài đặt ID Game & Thời gian quét (Delay)")
    print(f"   {C_GREEN}[4]{C_RESET} 🛑 Kill toàn bộ tab Roblox ngay lập tức")
    print(f"   {C_GREEN}[5]{C_RESET} 📊 Kiểm tra danh sách & Trạng thái In-Game chi tiết")
    print(f"   {C_GREEN}[6]{C_RESET} 🗑️  Xóa tài khoản (Xóa lẻ theo STT hoặc Xóa sạch)")
    print(f"   {C_RED}[0]{C_RESET} 🚪 Thoát chương trình")
    
    choice = input(f"\n{C_CYAN}   ➜ Nhập lựa chọn của bạn [0-6]: {C_RESET}").strip()

    if choice == "1":
        run_auto_rejoin(cfg)
    elif choice == "2":
        os.system("clear")
        print(f"{C_CYAN}=== THÊM TÀI KHOẢN MỚI (QUÉT PACKAGE) ==={C_RESET}")
        pkgs = scan_packages()
        if pkgs:
            print(f"{C_GREEN}[+] Tìm thấy các bản Roblox/Clone trên máy bạn:{C_RESET}")
            for i, p in enumerate(pkgs):
                print(f"    {C_YELLOW}[{i+1}]{C_RESET} {p}")
            sel = input(f"\n{C_CYAN}➔ Chọn số thứ tự package (hoặc nhập tên tùy chỉnh): {C_RESET}").strip()
            pkg = pkgs[int(sel)-1] if sel.isdigit() and 1 <= int(sel) <= len(pkgs) else sel
        else:
            pkg = input(f"{C_YELLOW}➔ Không quét thấy tự động, hãy nhập tên Package (vd: com.roblox.client): {C_RESET}").strip()
        
        ck = input(f"{C_CYAN}➔ Dán chuỗi Cookie (.ROBLOSECURITY): {C_RESET}").strip()
        print(f"{C_YELLOW}[⏳] Đang xác thực Cookie với máy chủ Roblox...{C_RESET}")
        uid, uname = verify_cookie(ck)
        
        if uid:
            cfg["accounts"] = [a for a in cfg["accounts"] if a["pkg"] != pkg]
            cfg["accounts"].append({"name": uname, "uid": uid, "pkg": pkg, "cookie": ck})
            save_cfg(cfg)
            print(f"\n{C_GREEN}[✔ THÀNH CÔNG] Đã lưu tài khoản: {C_BOLD}{uname}{C_RESET} {C_GREEN}(ID: {uid}) vào package {pkg}!{C_RESET}")
        else:
            print(f"\n{C_RED}[❌ LỖI] Cookie không hợp lệ hoặc đã hết hạn. Vui lòng kiểm tra lại!{C_RESET}")
        input(f"\n{C_DIM}Bấm Enter để quay lại menu chính...{C_RESET}")
        
    elif choice == "3":
        os.system("clear")
        print(f"{C_CYAN}=== CÀI ĐẶT THÔNG SỐ HỆ THỐNG ==={C_RESET}")
        gid = input(f"{C_YELLOW}➔ Nhập ID Game mới (Enter để giữ nguyên [{cfg['game_id']}]): {C_RESET}").strip()
        dl = input(f"{C_YELLOW}➔ Nhập thời gian Delay quét giây (Enter để giữ nguyên [{cfg.get('delay', 20)}]s): {C_RESET}").strip()
        
        if gid: cfg["game_id"] = gid
        if dl.isdigit(): cfg["delay"] = int(dl)
        save_cfg(cfg)
        print(f"\n{C_GREEN}[✔] Đã cập nhật cấu hình thành công!{C_RESET}")
        time.sleep(1.5)
        
    elif choice == "4":
        os.system("clear")
        print(f"{C_YELLOW}[⏳] Đang tiến hành ép dừng toàn bộ các tab Roblox...{C_RESET}")
        for a in cfg["accounts"]:
            os.system(f"am force-stop {a['pkg']}")
        print(f"{C_GREEN}[✔] Đã đóng tất cả các tiến trình Roblox thành công!{C_RESET}")
        input(f"\n{C_DIM}Bấm Enter để quay lại menu chính...{C_RESET}")
        
    elif choice == "5":
        os.system("clear")
        print(f"{C_CYAN}╔════════════════════════════════════════════════════╗{C_RESET}")
        print(f"{C_CYAN}║{C_BOLD}         KIỂM TRA TRẠNG THÁI TAB TRỰC TUYẾN          {C_RESET}{C_CYAN}║{C_RESET}")
        print(f"{C_CYAN}╚════════════════════════════════════════════════════╝{C_RESET}")
        if not cfg["accounts"]:
            print(f"{C_RED}  (Chưa có tài khoản nào được lưu trong danh sách){C_RESET}")
        for i, a in enumerate(cfg["accounts"]):
            pid = os.popen(f"pidof {a['pkg']}").read().strip()
            ig = is_in_game(a["uid"])
            app_status = f"{C_GREEN}RUNNING (PID: {pid}){C_RESET}" if pid else f"{C_RED}CLOSED{C_RESET}"
            game_status = f"{C_GREEN}🎮 IN-GAME{C_RESET}" if ig else f"{C_RED}❌ DISCONNECTED{C_RESET}"
            print(f"  {C_BOLD}[{i+1}]{C_RESET} {C_YELLOW}{a['name']}{C_RESET}")
            print(f"      Package : {a['pkg']}")
            print(f"      App     : {app_status}")
            print(f"      Trạng thái: {game_status}")
            print(f"  {C_DIM}------------------------------------------------{C_RESET}")
        input(f"\n{C_CYAN}Bấm Enter để quay lại menu chính...{C_RESET}")
        
    elif choice == "6":
        os.system("clear")
        print(f"{C_CYAN}=== QUẢN LÝ / XÓA TÀI KHOẢN ==={C_RESET}")
        if not cfg["accounts"]:
            print(f"{C_RED}Danh sách trống!{C_RESET}")
            time.sleep(1.5)
            continue
        for i, a in enumerate(cfg["accounts"]):
            print(f"  [{i+1}] {a['name']} ({a['pkg']})")
        x = input(f"\n{C_YELLOW}➔ Nhập số thứ tự cần xóa (hoặc gõ chữ 'all' để xóa toàn bộ): {C_RESET}").strip()
        if x.lower() == "all":
            cfg["accounts"] = []
            print(f"{C_GREEN}[✔] Đã xóa toàn bộ danh sách tài khoản!{C_RESET}")
        elif x.isdigit() and 1 <= int(x) <= len(cfg["accounts"]):
            removed = cfg["accounts"].pop(int(x)-1)
            print(f"{C_GREEN}[✔] Đã xóa tài khoản: {removed['name']}!{C_RESET}")
        save_cfg(cfg)
        time.sleep(1.5)
        
    elif choice == "0":
        os.system("clear")
        print(f"{C_CYAN}Cảm ơn bạn đã sử dụng tools BAOTUE. Hẹn gặp lại!{C_RESET}")
        break
