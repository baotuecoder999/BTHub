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
C_DIM = "\033[2m"
C_RESET = "\033[0m"

def load_cfg():
    if os.path.exists(CFG_PATH):
        with open(CFG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"game_id": "2753915549", "delay": 20, "packages": [], "accounts": []}

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
    print(f"{C_YELLOW}[⏳] Đang làm mới & khởi chạy cho: {C_PURPLE}{username}{C_RESET} {C_DIM}({pkg}){C_RESET}")
    os.system(f"am force-stop {pkg}")
    time.sleep(2)
    ticket = get_auth_ticket(cookie)
    if not ticket:
        print(f"{C_RED}[❌] Lỗi: Cookie của {username} đã hết hạn!{C_RESET}")
        return
    url = f"roblox://placeId={game_id}&ticket={ticket}"
    os.system(f'am start -n {pkg}/com.roblox.client.ActivityProtocolLaunch -a android.intent.action.VIEW -d "{url}" > /dev/null 2>&1')
    print(f"{C_GREEN}[✔] Đã gửi lệnh vào Game ID {game_id} thành công!{C_RESET}")

def run_auto_rejoin(cfg):
    if not cfg["accounts"]:
        print(f"\n{C_RED}[!] Chưa có tài khoản nào được cấu hình cookie!{C_RESET}")
        time.sleep(2)
        return
    
    os.system("clear")
    print(f"{C_CYAN}╔════════════════════════════════════════════╗{C_RESET}")
    print(f"{C_CYAN}║{C_PURPLE}       HỆ THỐNG AUTO-REJOIN ĐANG CHẠY       {C_RESET}{C_CYAN}║{C_RESET}")
    print(f"{C_CYAN}╚════════════════════════════════════════════╝{C_RESET}")
    print(f"{C_YELLOW}[*] Game ID Mục tiêu : {C_CYAN}{cfg['game_id']}{C_RESET}")
    print(f"{C_YELLOW}[*] Thời gian quét   : {C_CYAN}{cfg.get('delay', 20)} giây/lần{C_RESET}")
    print(f"{C_DIM}--------------------------------------------{C_RESET}")

    print(f"{C_PURPLE}[🚀] Đang khởi động toàn bộ các tab lần đầu...{C_RESET}")
    for acc in cfg["accounts"]:
        launch_tab(acc["pkg"], cfg["game_id"], acc["cookie"], acc["name"])
        time.sleep(6)

    print(f"\n{C_GREEN}[⚡] ĐÃ KÍCH HOẠT CHẾ ĐỘ GIÁM SÁT TỰ ĐỘNG!{C_RESET}")
    print(f"{C_DIM}(Nhấn Ctrl + C để dừng lại bất cứ lúc nào){C_RESET}\n")
    
    try:
        while True:
            print(f"{C_DIM}--------------------------------------------{C_RESET}")
            print(f"{C_CYAN}[⏰ Kiểm tra lúc: {time.strftime('%H:%M:%S')}]{C_RESET}")
            for acc in cfg["accounts"]:
                pid = os.popen(f"pidof {acc['pkg']}").read().strip()
                ingame = is_in_game(acc["uid"])
                
                if not pid or not ingame:
                    reason = "Mất tiến trình App" if not pid else "Bị văng khỏi Game"
                    print(f"{C_RED}[⚠ VĂNG] {acc['name']} -> {reason}! Đang Rejoin...{C_RESET}")
                    launch_tab(acc["pkg"], cfg["game_id"], acc["cookie"], acc["name"])
                    time.sleep(8)
                else:
                    print(f"{C_GREEN}[✔ ONLINE] {acc['name']} {C_DIM}({acc['pkg']}) -> Đang cày ổn định.{C_RESET}")
            
            time.sleep(cfg.get("delay", 20))
    except KeyboardInterrupt:
        print(f"\n{C_YELLOW}[!] Đã dừng chế độ Auto-Rejoin.{C_RESET}")
        time.sleep(1.5)

while True:
    os.system("clear")
    cfg = load_cfg()
    
    print(f"{C_CYAN}╔════════════════════════════════════════════════════╗{C_RESET}")
    print(f"{C_CYAN}║{C_PURPLE}             ⚡ BAOTUE REJOIN PRO V10 ⚡             {C_RESET}{C_CYAN}║{C_RESET}")
    print(f"{C_CYAN}╠════════════════════════════════════════════════════╣{C_RESET}")
    print(f"{C_CYAN}║{C_RESET} {C_YELLOW}Game ID Hiện Tại :{C_RESET} {cfg['game_id']:<26}{C_CYAN}║{C_RESET}")
    print(f"{C_CYAN}║{C_RESET} {C_YELLOW}Package Đã Lưu   :{C_RESET} {str(len(cfg.get('packages', []))):<26}{C_CYAN}║{C_RESET}")
    print(f"{C_CYAN}║{C_RESET} {C_YELLOW}Tài khoản Cookie :{C_RESET} {str(len(cfg['accounts'])) + ' nick':<26}{C_CYAN}║{C_RESET}")
    print(f"{C_CYAN}╚════════════════════════════════════════════════════╝{C_RESET}")
    
    print(f"\n{C_CYAN}   CHỌN CHỨC NĂNG HỆ THỐNG:{C_RESET}")
    print(f"   {C_GREEN}[1]{C_RESET} 🚀 Khởi động tất cả tab & Chạy Auto-Rejoin")
    print(f"   {C_GREEN}[2]{C_RESET} 📦 Quét & Thêm danh sách Package Roblox")
    print(f"   {C_GREEN}[3]{C_RESET} 🍪 Nhập Cookie & Gắn vào tài khoản")
    print(f"   {C_GREEN}[4]{C_RESET} ⚙️  Cài đặt ID Game & Thời gian quét (Delay)")
    print(f"   {C_GREEN}[5]{C_RESET} 🛑 Kill toàn bộ tab Roblox ngay lập tức")
    print(f"   {C_GREEN}[6]{C_RESET} 📊 Kiểm tra trạng thái In-Game chi tiết")
    print(f"   {C_GREEN}[7]{C_RESET} 🗑️  Quản lý / Xóa tài khoản hoặc Package")
    print(f"   {C_RED}[0]{C_RESET} 🚪 Thoát chương trình")
    
    choice = input(f"\n{C_CYAN}   ➜ Nhập lựa chọn [0-7]: {C_RESET}").strip()

    if choice == "1":
        run_auto_rejoin(cfg)
        
    elif choice == "2":
        os.system("clear")
        print(f"{C_CYAN}=== QUẢN LÝ PACKAGE ROBLOX ==={C_RESET}")
        detected = scan_packages()
        print(f"{C_GREEN}[+] Các bản Roblox / Clone quét được trên máy:{C_RESET}")
        if detected:
            for i, p in enumerate(detected):
                print(f"    {C_YELLOW}[{i+1}]{C_RESET} {p}")
        else:
            print(f"    {C_RED}(Không tìm thấy package nào tự động){C_RESET}")
            
        print(f"\n{C_PURPLE}Các Package hiện đang lưu trong tool:{C_RESET}")
        saved_pkgs = cfg.get("packages", [])
        if saved_pkgs:
            for i, p in enumerate(saved_pkgs):
                print(f"    - [{i+1}] {p}")
        else:
            print(f"    {C_RED}(Chưa lưu package nào){C_RESET}")
            
        action = input(f"\n{C_CYAN}Nhập STT package quét được để thêm (hoặc gõ trực tiếp tên package): {C_RESET}").strip()
        if action.isdigit() and detected and 1 <= int(action) <= len(detected):
            chosen_pkg = detected[int(action)-1]
        else:
            chosen_pkg = action
            
        if chosen_pkg and chosen_pkg not in saved_pkgs:
            cfg.setdefault("packages", []).append(chosen_pkg)
            save_cfg(cfg)
            print(f"{C_GREEN}[✔] Đã thêm package: {chosen_pkg}{C_RESET}")
        else:
            print(f"{C_RED}[!] Package trống hoặc đã tồn tại!{C_RESET}")
        input(f"\n{C_DIM}Bấm Enter để tiếp tục...{C_RESET}")
        
    elif choice == "3":
        os.system("clear")
        print(f"{C_CYAN}=== NHẬP COOKIE & GẮN TÀI KHOẢN ==={C_RESET}")
        saved_pkgs = cfg.get("packages", [])
        if not saved_pkgs:
            print(f"{C_RED}[!] Bạn chưa thêm Package nào! Vui lòng vào mục [2] để thêm package trước.{C_RESET}")
            input(f"\n{C_DIM}Bấm Enter để quay lại...{C_RESET}")
            continue
            
        print(f"{C_GREEN}Chọn Package để gắn tài khoản này:{C_RESET}")
        for i, p in enumerate(saved_pkgs):
            print(f"    {C_YELLOW}[{i+1}]{C_RESET} {p}")
            
        pkg_sel = input(f"\n{C_CYAN}➔ Chọn số thứ tự package: {C_RESET}").strip()
        if pkg_sel.isdigit() and 1 <= int(pkg_sel) <= len(saved_pkgs):
            target_pkg = saved_pkgs[int(pkg_sel)-1]
        else:
            print(f"{C_RED}[!] Lựa chọn không hợp lệ!{C_RESET}")
            time.sleep(1.5)
            continue
            
        ck = input(f"{C_CYAN}➔ Dán chuỗi Cookie (.ROBLOSECURITY): {C_RESET}").strip()
        print(f"{C_YELLOW}[⏳] Đang xác thực Cookie với Roblox...{C_RESET}")
        uid, uname = verify_cookie(ck)
        
        if uid:
            cfg["accounts"] = [a for a in cfg["accounts"] if a["pkg"] != target_pkg]
            cfg["accounts"].append({"name": uname, "uid": uid, "pkg": target_pkg, "cookie": ck})
            save_cfg(cfg)
            print(f"\n{C_GREEN}[✔ THÀNH CÔNG] Đã gắn nick {C_PURPLE}{uname}{C_GREEN} (ID: {uid}) vào {target_pkg}!{C_RESET}")
        else:
            print(f"\n{C_RED}[❌ LỖI] Cookie không hợp lệ hoặc đã chết!{C_RESET}")
        input(f"\n{C_DIM}Bấm Enter để quay lại menu...{C_RESET}")
        
    elif choice == "4":
        os.system("clear")
        print(f"{C_CYAN}=== CÀI ĐẶT THÔNG SỐ HỆ THỐNG ==={C_RESET}")
        gid = input(f"{C_YELLOW}➔ Nhập ID Game mới (Enter giữ nguyên [{cfg['game_id']}]): {C_RESET}").strip()
        dl = input(f"{C_YELLOW}➔ Nhập Delay giây (Enter giữ nguyên [{cfg.get('delay', 20)}]s): {C_RESET}").strip()
        if gid: cfg["game_id"] = gid
        if dl.isdigit(): cfg["delay"] = int(dl)
        save_cfg(cfg)
        print(f"{C_GREEN}[✔] Đã cập nhật thành công!{C_RESET}")
        time.sleep(1.5)
        
    elif choice == "5":
        os.system("clear")
        print(f"{C_YELLOW}[⏳] Đang ép dừng toàn bộ tab Roblox...{C_RESET}")
        for a in cfg["accounts"]:
            os.system(f"am force-stop {a['pkg']}")
        print(f"{C_GREEN}[✔] Đã đóng xong!{C_RESET}")
        input(f"\n{C_DIM}Bấm Enter để quay lại...{C_RESET}")
        
    elif choice == "6":
        os.system("clear")
        print(f"{C_CYAN}╔════════════════════════════════════════════════════╗{C_RESET}")
        print(f"{C_CYAN}║{C_PURPLE}         KIỂM TRA TRẠNG THÁI IN-GAME CHI TIẾT          {C_RESET}{C_CYAN}║{C_RESET}")
        print(f"{C_CYAN}╚════════════════════════════════════════════════════╝{C_RESET}")
        if not cfg["accounts"]:
            print(f"{C_RED}  (Chưa có tài khoản nào được cấu hình){C_RESET}")
        for i, a in enumerate(cfg["accounts"]):
            pid = os.popen(f"pidof {a['pkg']}").read().strip()
            ig = is_in_game(a["uid"])
            app_st = f"{C_GREEN}RUNNING (PID: {pid}){C_RESET}" if pid else f"{C_RED}CLOSED{C_RESET}"
            game_st = f"{C_GREEN}🎮 IN-GAME{C_RESET}" if ig else f"{C_RED}❌ DISCONNECTED{C_RESET}"
            print(f"  {C_PURPLE}[{i+1}] {a['name']}{C_RESET}")
            print(f"      Package : {a['pkg']}")
            print(f"      App     : {app_st}")
            print(f"      Trạng thái: {game_st}")
            print(f"  {C_DIM}------------------------------------------------{C_RESET}")
        input(f"\n{C_CYAN}Bấm Enter để quay lại menu...{C_RESET}")
        
    elif choice == "7":
        os.system("clear")
        print(f"{C_CYAN}=== QUẢN LÝ / XÓA DỮ LIỆU ==={C_RESET}")
        print(f"1. Xóa tài khoản (Account)")
        print(f"2. Xóa Package đã lưu")
        sub = input(f"Chọn mục muốn xóa [1-2]: ").strip()
        if sub == "1":
            for i, a in enumerate(cfg["accounts"]):
                print(f"  [{i+1}] {a['name']} ({a['pkg']})")
            x = input("Nhập STT tài khoản muốn xóa (hoặc gõ 'all'): ").strip()
            if x.lower() == "all": cfg["accounts"] = []
            elif x.isdigit() and 1 <= int(x) <= len(cfg["accounts"]): cfg["accounts"].pop(int(x)-1)
        elif sub == "2":
            for i, p in enumerate(cfg.get("packages", [])):
                print(f"  [{i+1}] {p}")
            x = input("Nhập STT package muốn xóa (hoặc gõ 'all'): ").strip()
            if x.lower() == "all": cfg["packages"] = []
            elif x.isdigit() and 1 <= int(x) <= len(cfg.get("packages", [])): cfg["packages"].pop(int(x)-1)
        save_cfg(cfg)
        print(f"{C_GREEN}[✔] Đã cập nhật lại dữ liệu!{C_RESET}")
        time.sleep(1.5)
        
    elif choice == "0":
        os.system("clear")
        print(f"{C_CYAN}Hẹn gặp lại bạn!{C_RESET}")
        break
