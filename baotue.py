code = """import os, time, json, requests
CFG_PATH = "/sdcard/Download/baotue_config.json"
C_CYAN, C_GREEN, C_YELLOW, C_RED, C_PURPLE, C_WHITE, C_BOLD, C_DIM, C_RESET = "\\033[96m", "\\033[92m", "\\033[93m", "\\033[91m", "\\033[95m", "\\033[97m", "\\033[1m", "\\033[2m", "\\033[0m"

def load_cfg():
    if os.path.exists(CFG_PATH):
        try:
            with open(CFG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("packages") and isinstance(data["packages"][0], str):
                    data["packages"] = [{"pkg": p, "active": True} for p in data["packages"]]
                return data
        except: pass
    return {"game_id": "2753915549", "delay": 20, "packages": [], "accounts": []}

def save_cfg(data):
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def scan_packages():
    found = set()
    q_out = os.popen('\x27cmd package query-activities -a android.intent.action.VIEW -d "roblox://" 2>/dev/null\x27').read()
    for line in q_out.splitlines():
        if "packageName=" in line:
            pkg = line.split("=", 1)[1].strip()
            if pkg: found.add(pkg)
    for line in os.popen("pm list packages -3").read().splitlines():
        pkg = line.replace("package:", "").strip()
        if any(k in pkg.lower() for k in ["roblox", "delta", "arceus", "codex", "fluxus", "noka"]):
            found.add(pkg)
    return sorted(list(found))

def verify_cookie(cookie):
    try:
        cookie = cookie.strip().strip(\x27"\x27).strip(\x27\x27\x27)
        if ".ROBLOSECURITY=" in cookie:
            cookie = cookie.split(".ROBLOSECURITY=")[1].split(";")[0]
        r = requests.get("https://users.roblox.com/v1/users/authenticated", cookies={".ROBLOSECURITY": cookie}, timeout=10)
        if r.status_code == 200:
            d = r.json()
            return str(d["id"]), d["name"], cookie
    except: pass
    return None, None, None

def is_in_game(uid):
    if not uid: return False
    try:
        r = requests.post("https://presence.roblox.com/v1/presence/users", json={"userIds": [int(uid)]}, timeout=10)
        if r.status_code == 200:
            return r.json()["userPresences"][0]["userPresenceType"] == 2
    except: pass
    return False

def get_auth_ticket(cookie):
    if not cookie: return None
    try:
        s = requests.Session()
        s.cookies[".ROBLOSECURITY"] = cookie
        headers = {"User-Agent": "Roblox/WinInet", "Referer": "https://www.roblox.com/"}
        r1 = s.post("https://auth.roblox.com/v1/authentication-ticket", headers=headers, timeout=10)
        if r1.headers.get("x-csrf-token"):
            headers["x-csrf-token"] = r1.headers.get("x-csrf-token")
        r2 = s.post("https://auth.roblox.com/v1/authentication-ticket", headers=headers, timeout=10)
        return r2.headers.get("rbx-authentication-ticket")
    except: pass
    return None

def launch_package_tab(pkg, game_id, acc_info=None):
    name = acc_info["name"] if acc_info else "Chưa gắn Cookie"
    print(f"\\n{C_YELLOW}{C_BOLD}  [⏳] ĐANG KÍCH HOẠT TAB: {pkg}{C_RESET}")
    print(f"       {C_WHITE}• Tài khoản : {C_PURPLE}{name}{C_RESET}")
    print(f"       {C_WHITE}• Join Game : {C_CYAN}{game_id}{C_RESET}")
    
    os.system(f"am force-stop {pkg} >/dev/null 2>&1")
    time.sleep(2)
    
    ticket = get_auth_ticket(acc_info["cookie"]) if (acc_info and acc_info.get("cookie")) else None
    if ticket:
        url = f"roblox://placeId={game_id}&ticket={ticket}"
        os.system(f'\x27am start -p {pkg} -a android.intent.action.VIEW -d "{url}" > /dev/null 2>&1\x27')
        print(f"{C_GREEN}{C_BOLD}  [✔] ĐÃ GỬI VÉ COOKIE & JOIN GAME ID {game_id}!{C_RESET}")
    else:
        os.system(f'\x27am start -p {pkg} > /dev/null 2>&1\x27')
        time.sleep(3)
        os.system(f'\x27am start -p {pkg} -a android.intent.action.VIEW -d "roblox://placeId={game_id}" > /dev/null 2>&1\x27')
        print(f"{C_GREEN}{C_BOLD}  [✔] ĐÃ MỞ APP & JOIN GAME ID {game_id}!{C_RESET}")

def run_auto_rejoin(cfg):
    active_pkgs = [p["pkg"] for p in cfg.get("packages", []) if p.get("active", True)]
    if not active_pkgs:
        # Fallback nếu chưa set packages mà có accounts cũ
        active_pkgs = [a["pkg"] for a in cfg.get("accounts", [])]
    if not active_pkgs:
        print(f"\\n{C_RED}{C_BOLD}  [!] CHƯA CÓ PACKAGE NÀO ĐƯỢC CHỌN! Hãy vào mục [2] để Bật.{C_RESET}")
        time.sleep(2); return
    
    acc_map = {a["pkg"]: a for a in cfg.get("accounts", [])}
    os.system("clear")
    print(f"{C_CYAN}{C_BOLD}=== AUTO-REJOIN ĐANG HOẠT ĐỘNG ==={C_RESET}\\n")
    for pkg in active_pkgs:
        launch_package_tab(pkg, cfg["game_id"], acc_map.get(pkg))
        time.sleep(5)
    print(f"\\n{C_GREEN}{C_BOLD}  [⚡] ĐÃ KÍCH HOẠT GIÁM SÁT! (Nhấn Ctrl + C để dừng){C_RESET}\\n")
    try:
        while True:
            for pkg in active_pkgs:
                acc = acc_map.get(pkg)
                pid = os.popen(f"pidof {pkg}").read().strip()
                if acc and acc.get("uid"):
                    if not pid or not is_in_game(acc["uid"]):
                        launch_package_tab(pkg, cfg["game_id"], acc)
                        time.sleep(8)
                else:
                    if not pid:
                        launch_package_tab(pkg, cfg["game_id"], None)
                        time.sleep(8)
            time.sleep(cfg.get("delay", 20))
    except KeyboardInterrupt:
        print(f"\\n{C_YELLOW}  [!] Đã dừng.{C_RESET}"); time.sleep(1)

while True:
    os.system("clear")
    c = load_cfg()
    pkgs = c.get("packages", [])
    active_count = sum(1 for p in pkgs if p.get("active", True))
    
    print(f"{C_CYAN}======================================\\n      TOOLS REJOIN ROBLOX - BAOTUE\\n======================================{C_RESET}")
    print(f"{C_YELLOW}Game ID:{C_RESET} {c[\"game_id\"]} | {C_YELLOW}Delay:{C_RESET} {c.get(\"delay\", 20)}s | {C_YELLOW}Active Pkg:{C_RESET} {active_count} | {C_YELLOW}Accs:{C_RESET} {len(c[\"accounts\"])}")
    print(f"{C_CYAN}--------------------------------------{C_RESET}")
    print(f"{C_GREEN}[1]{C_RESET} Bat dau Auto-Rejoin (Theo Package da Set)")
    print(f"{C_GREEN}[2]{C_RESET} Set Package & Chon Package chay")
    print(f"{C_GREEN}[3]{C_RESET} Nhap nhieu Cookie hang loat vao Package")
    print(f"{C_GREEN}[4]{C_RESET} Set ID Game & Delay")
    print(f"{C_GREEN}[5]{C_RESET} Kill tat ca Tab Roblox")
    print(f"{C_GREEN}[6]{C_RESET} Kiem tra trang thai In-Game")
    print(f"{C_GREEN}[7]{C_RESET} Xoa tai khoan hoac Package")
    print(f"{C_RED}[0]{C_RESET} Thoat")
    ch = input(f"{C_CYAN}\\n>>> Chon chuc nang: {C_RESET}").strip()
    
    if ch == "1": run_auto_rejoin(c)
    elif ch == "2":
        while True:
            os.system("clear")
            c = load_cfg()
            saved = c.get("packages", [])
            print(f"{C_CYAN}=== QUẢN LÝ & CHỌN PACKAGE CHẠY ==={C_RESET}\\n")
            if saved:
                for i, it in enumerate(saved):
                    st = f"{C_GREEN}[✔ BẬT]{C_RESET}" if it.get("active", True) else f"{C_RED}[✖ TẮT]{C_RESET}"
                    print(f"  [{i+1}] {st} {it['pkg']}")
            else:
                print("  (Chưa có package nào)")
            print(f"\\n  [A] Quét tất cả app trên máy\\n  [B] Bật tất cả | [C] Tắt tất cả\\n  [Số STT] Bật/Tắt lẻ (vd: 1,2)\\n  [0] Quay lại")
            sub = input("\\n  Chọn: ").strip()
            if sub == "0": break
            elif sub.upper() == "A":
                for p in scan_packages():
                    if p not in [x["pkg"] for x in saved]: saved.append({"pkg": p, "active": True})
                c["packages"] = saved; save_cfg(c)
            elif sub.upper() == "B":
                for it in saved: it["active"] = True
                save_cfg(c)
            elif sub.upper() == "C":
                for it in saved: it["active"] = False
                save_cfg(c)
            elif sub.isdigit() or "," in sub:
                for p in sub.split(","):
                    if p.strip().isdigit():
                        idx = int(p.strip()) - 1
                        if 0 <= idx < len(saved): saved[idx]["active"] = not saved[idx].get("active", True)
                c["packages"] = saved; save_cfg(c)
    elif ch == "3":
        os.system("clear")
        c = load_cfg()
        saved = c.get("packages", [])
        if not saved:
            input("Chưa có Package nào! Vào mục [2] quét và thêm package trước. Bấm Enter..."); continue
        print("DANH SÁCH PACKAGE HIỆN CÓ:")
        for i, it in enumerate(saved):
            print(f"  [{i+1}] {it['pkg']}")
        print("\\nDán danh sách Cookie (mỗi dòng 1 cái). Gõ END ở dòng cuối để kết thúc:")
        lines = []
        while True:
            try:
                l = input()
                if l.strip().upper() == "END" or not l.strip(): break
                lines.append(l.strip())
            except: break
        raw = [c for c in "".join(lines).split() if len(c) > 50 or ".ROBLOSECURITY" in c]
        for idx, rck in enumerate(raw):
            if idx >= len(saved): break
            pkg = saved[idx]["pkg"]
            uid, uname, vck = verify_cookie(rck)
            if uid:
                c["accounts"] = [a for a in c["accounts"] if a["pkg"] != pkg]
                c["accounts"].append({"name": uname, "uid": uid, "pkg": pkg, "cookie": vck})
                print(f"  [✔] Gắn thành công: {uname} -> {pkg}")
            else:
                print(f"  [✖] Cookie thứ {idx+1} không hợp lệ, bỏ qua.")
        save_cfg(c); input("\\nHoàn tất! Bấm Enter...")
    elif ch == "4":
        g = input(f"ID Game mới (giu nguyen {c[\"game_id\"]}) : ").strip()
        d = input(f"Delay giay (giu nguyen {c.get(\"delay\", 20)}): ").strip()
        if g: c["game_id"] = g
        if d.isdigit(): c["delay"] = int(d)
        save_cfg(c)
        print(f"{C_GREEN}[+] Da cap nhat!{C_RESET}"); time.sleep(1)
    elif ch == "5":
        for it in c.get("packages", []): os.system(f"am force-stop {it['pkg']} >/dev/null 2>&1")
        print(f"{C_YELLOW}[!] Da kill het tab!{C_RESET}"); time.sleep(1.5)
    elif ch == "6":
        os.system("clear")
        saved = c.get("packages", [])
        acc_map = {a["pkg"]: a for a in c.get("accounts", [])}
        for i, it in enumerate(saved):
            pkg = it["pkg"]
            acc = acc_map.get(pkg)
            pid = os.popen(f"pidof {pkg}").read().strip()
            ig = is_in_game(acc["uid"]) if acc else False
            print(f"[{i+1}] {pkg} | App: {'ON' if pid else 'OFF'} | Nick: {acc['name'] if acc else 'Chưa gắn'} | Game: {'IN-GAME' if ig else 'DISCONNECT'}")
        input("\\nNhan Enter de quay lai...")
    elif ch == "7":
        sub = input("Xóa [1] Tài khoản hay [2] Package? ").strip()
        if sub == "1": c["accounts"] = []
        elif sub == "2": c["packages"] = []
        save_cfg(c); print("Đã xóa!"); time.sleep(1)
    elif ch == "0": break
"""
open("/sdcard/Download/baotue.py", "w", encoding="utf-8").write(code)
print("Cập nhật thành công!")
' && echo 'alias baotue="python /sdcard/Download/baotue.py"' >> ~/.bashrc && source ~/.bashrc && baotue
