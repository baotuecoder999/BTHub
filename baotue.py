import os
import time
import json
import requests

CFG_PATH = "/sdcard/Download/baotue_config.json"

G, R, Y, C, W = "\033[92m", "\033[91m", "\033[93m", "\033[96m", "\033[0m"

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
    print(f"{Y}[BAOTUE] Dang kill & khoi dong lai {username} ({pkg})...{W}")
    os.system(f"am force-stop {pkg}")
    time.sleep(2)
    ticket = get_auth_ticket(cookie)
    if not ticket:
        print(f"{R}[BAOTUE] Loi: Cookie cua {username} da het han!{W}")
        return
    url = f"roblox://placeId={game_id}&ticket={ticket}"
    os.system(f'am start -n {pkg}/com.roblox.client.ActivityProtocolLaunch -a android.intent.action.VIEW -d "{url}" > /dev/null 2>&1')
    print(f"{G}[BAOTUE] Da gui lenh vao Game ID {game_id} cho {username}!{W}")

def run_auto_rejoin(cfg):
    if not cfg["accounts"]:
        print(f"{R}[!] Chua co tai khoan nao! Chon muc [2] de setup.{W}")
        time.sleep(2)
        return
    print(f"{C}[BAOTUE] Khoi dong toan bo tab lan dau...{W}")
    for acc in cfg["accounts"]:
        launch_tab(acc["pkg"], cfg["game_id"], acc["cookie"], acc["name"])
        time.sleep(8)

    print(f"{G}[BAOTUE] Dang giam sat Auto-Rejoin (Nhan Ctrl+C de dung)...{W}")
    try:
        while True:
            for acc in cfg["accounts"]:
                pid = os.popen(f"pidof {acc['pkg']}").read().strip()
                ingame = is_in_game(acc["uid"])
                if not pid or not ingame:
                    print(f"{R}[!] {acc['name']} mat ket noi (App:{bool(pid)} | InGame:{ingame}) -> Rejoin!{W}")
                    launch_tab(acc["pkg"], cfg["game_id"], acc["cookie"], acc["name"])
                    time.sleep(10)
                else:
                    print(f"{G}[OK] {acc['name']} ({acc['pkg']}) dang hoat dong on dinh.{W}")
            time.sleep(cfg.get("delay", 20))
    except KeyboardInterrupt:
        print(f"\n{Y}[BAOTUE] Da dung giam sat.{W}")

while True:
    os.system("clear")
    cfg = load_cfg()
    print(f"{C}============================================")
    print(f"       TOOLS REJOIN ROBLOX - BAOTUE         ")
    print(f"============================================{W}")
    print(f"{Y}Game ID:{W} {cfg['game_id']} | {Y}Delay:{W} {cfg.get('delay', 20)}s | {Y}Tabs:{W} {len(cfg['accounts'])}")
    print(f"{C}--------------------------------------------{W}")
    print(f"{G}[1]{W} Bat dau Auto-Rejoin (Tat ca Tab)")
    print(f"{G}[2]{W} Quet Package & Them Cookie tai khoan")
    print(f"{G}[3]{W} Cai dat ID Game & Thoi gian quet (Delay)")
    print(f"{G}[4]{W} Kill tat ca Tab Roblox ngay lap tuc")
    print(f"{G}[5]{W} Kiem tra danh sach & Trang thai In-Game")
    print(f"{G}[6]{W} Xoa tai khoan (Theo STT hoac Xoa het)")
    print(f"{R}[0]{W} Thoat Tool")
    choice = input(f"{C}\n>>> Nhap lua chon: {W}").strip()

    if choice == "1":
        run_auto_rejoin(cfg)
    elif choice == "2":
        pkgs = scan_packages()
        if pkgs:
            print(f"{G}[+] Cac goi Roblox tim thay tren may:{W}")
            for i, p in enumerate(pkgs):
                print(f"  {i+1}. {p}")
            sel = input("Chon STT package (hoac nhap ten package): ").strip()
            pkg = pkgs[int(sel)-1] if sel.isdigit() and 1 <= int(sel) <= len(pkgs) else sel
        else:
            pkg = input("Nhap ten Package (vd: com.roblox.client): ").strip()
        ck = input("Dan Cookie (.ROBLOSECURITY): ").strip()
        uid, uname = verify_cookie(ck)
        if uid:
            cfg["accounts"] = [a for a in cfg["accounts"] if a["pkg"] != pkg]
            cfg["accounts"].append({"name": uname, "uid": uid, "pkg": pkg, "cookie": ck})
            save_cfg(cfg)
            print(f"{G}[+] Da luu {uname} (ID: {uid}) -> {pkg}!{W}")
        else:
            print(f"{R}[!] Cookie khong hop le hoac da het han!{W}")
        time.sleep(2)
    elif choice == "3":
        gid = input(f"Nhap ID Game moi (Enter giu nguyen {cfg['game_id']}): ").strip()
        dl = input(f"Nhap Delay giay (Enter giu nguyen {cfg.get('delay', 20)}): ").strip()
        if gid: cfg["game_id"] = gid
        if dl.isdigit(): cfg["delay"] = int(dl)
        save_cfg(cfg)
        print(f"{G}[+] Da cap nhat cau hinh!{W}")
        time.sleep(1.5)
    elif choice == "4":
        for a in cfg["accounts"]:
            os.system(f"am force-stop {a['pkg']}")
        print(f"{Y}[!] Da kill toan bo tab Roblox!{W}")
        time.sleep(1.5)
    elif choice == "5":
        for i, a in enumerate(cfg["accounts"]):
            pid = os.popen(f"pidof {a['pkg']}").read().strip()
            ig = is_in_game(a["uid"])
            print(f"{i+1}. {a['name']} | {a['pkg']} -> App: {G+'ON'+W if pid else R+'OFF'+W} | Game: {G+'IN-GAME'+W if ig else R+'DISCONNECT'+W}")
        input("\nNhan Enter de quay lai...")
    elif choice == "6":
        for i, a in enumerate(cfg["accounts"]):
            print(f"{i+1}. {a['name']} ({a['pkg']})")
        x = input("Nhap STT can xoa (hoac go 'all'): ").strip()
        if x == "all":
            cfg["accounts"] = []
        elif x.isdigit() and 1 <= int(x) <= len(cfg["accounts"]):
            cfg["accounts"].pop(int(x)-1)
        save_cfg(cfg)
        print(f"{Y}[+] Da xoa!{W}")
        time.sleep(1)
    elif choice == "0":
        break
