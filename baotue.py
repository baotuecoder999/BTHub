import sys
import glob

# Tự động nạp mọi thư viện site-packages của Python trong Termux
for _p in glob.glob("/data/data/com.termux/files/usr/lib/python*/site-packages"):
    if _p not in sys.path:
        sys.path.append(_p)
for _p in glob.glob("/data/data/com.termux/files/usr/local/lib/python*/site-packages"):
    if _p not in sys.path:
        sys.path.append(_p)

import os
import re
import shlex
import shutil
import sqlite3
import subprocess
import tempfile
import time
import json

try:
    import requests
except ImportError:
    os.system("pip install --break-system-packages --no-cache-dir requests >/dev/null 2>&1 || pkg install -y python-requests >/dev/null 2>&1")
    import requests

def get_cfg_path():
    sd_dir = "/sdcard/Download"
    try:
        os.makedirs(sd_dir, exist_ok=True)
        test_file = os.path.join(sd_dir, ".baotue_write_test")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        return os.path.join(sd_dir, "baotue_config.json")
    except Exception:
        return os.path.expanduser("~/baotue_config.json")

CFG_PATH = get_cfg_path()

def _is_root_uid():
    geteuid = getattr(os, "geteuid", None)
    return bool(geteuid and geteuid() == 0)

def has_root():
    try:
        if _is_root_uid():
            return True
        res = subprocess.run(
            ["su", "-c", "id -u"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        )
        return res.returncode == 0 and res.stdout.strip() == "0"
    except Exception:
        return False

HAS_ROOT = has_root()

def run_shell(cmd, timeout=30):
    try:
        if HAS_ROOT and not _is_root_uid():
            argv = ["su", "-c", cmd]
        else:
            argv = ["sh", "-c", cmd]
        res = subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=timeout,
        )
        return res.stdout or ""
    except Exception:
        return ""

def exec_shell(cmd, timeout=30):
    try:
        if HAS_ROOT and not _is_root_uid():
            argv = ["su", "-c", cmd]
        else:
            argv = ["sh", "-c", cmd]
        res = subprocess.run(
            argv,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
        )
        return res.returncode
    except Exception:
        return 1

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
        top_out = run_shell("top -n 1 -b | grep -i 'cpu'")
        if not top_out.strip():
            top_out = run_shell("top -n 1 -d 1")
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
    q_out = run_shell('cmd package query-activities -a android.intent.action.VIEW -d "roblox://"')
    for line in q_out.splitlines():
        line = line.strip()
        if line.startswith("packageName="):
            pkg = line.split("=", 1)[1].strip()
            if pkg:
                found.add(pkg)

    keywords = ["roblox", "delta", "arceus", "codex", "fluxus", "hydrogen", "vega", "trigon", "evon", "noka"]
    all_pkgs = run_shell("pm list packages -3").splitlines()
    for line in all_pkgs:
        pkg = line.replace("package:", "").strip()
        if any(k in pkg.lower() for k in keywords):
            found.add(pkg)

    return sorted(list(found))

CHROME_EPOCH_OFFSET = 11644473600
COOKIE_TTL_DAYS = 365
ROBLOX_PREFS_USER_KEYS = ("userid_long", "username", "displayName", "under13")
LAUNCH_GRACE_SECONDS = 45
ROBLOX_HTTP_UA = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36"

def normalize_cookie(raw_cookie):
    if not raw_cookie:
        return ""
    ck = raw_cookie.strip().strip('"').strip("'")
    if ".ROBLOSECURITY=" in ck:
        ck = ck.split(".ROBLOSECURITY=", 1)[1].split(";", 1)[0].strip()
    warn_idx = ck.find("_|WARNING:")
    if warn_idx != -1:
        ck = ck[warn_idx:].strip()
    if ";" in ck:
        ck = ck.split(";", 1)[0].strip()
    return ck.strip().strip('"').strip("'")

def verify_cookie(cookie):
    try:
        ck = normalize_cookie(cookie)
        if not ck:
            return None, None, None

        r = requests.get(
            "https://users.roblox.com/v1/users/authenticated",
            cookies={".ROBLOSECURITY": ck},
            headers={"User-Agent": ROBLOX_HTTP_UA},
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            return str(data["id"]), data["name"], ck
    except Exception:
        pass
    return None, None, None

def is_in_game(user_id, cookie=None):
    if not user_id:
        return None
    try:
        cookies = {".ROBLOSECURITY": normalize_cookie(cookie)} if cookie else None
        r = requests.post(
            "https://presence.roblox.com/v1/presence/users",
            json={"userIds": [int(user_id)]},
            cookies=cookies,
            headers={"User-Agent": ROBLOX_HTTP_UA},
            timeout=10,
        )
        if r.status_code == 200:
            presences = r.json().get("userPresences", [])
            if presences:
                return presences[0].get("userPresenceType") == 2
        return None
    except Exception:
        return None

def get_auth_ticket(cookie):
    ck = normalize_cookie(cookie)
    if not ck:
        return None
    try:
        s = requests.Session()
        s.cookies[".ROBLOSECURITY"] = ck
        headers = {
            "User-Agent": "Roblox/WinInet",
            "Referer": "https://www.roblox.com/",
        }
        r1 = s.post("https://auth.roblox.com/v1/authentication-ticket", headers=headers, timeout=10)
        csrf = r1.headers.get("x-csrf-token")
        if csrf:
            headers["x-csrf-token"] = csrf

        r2 = s.post("https://auth.roblox.com/v1/authentication-ticket", headers=headers, timeout=10)
        return r2.headers.get("rbx-authentication-ticket")
    except Exception:
        return None

def has_error_279(pkg, pid=None):
    """Kiểm tra log hệ thống gần nhất xem package có dính lỗi Error 279 hay không."""
    try:
        if pid is None:
            pid = run_shell(f"pidof {shlex.quote(pkg)}").strip()
        if not pid:
            return False
        pids = set(pid.split())
        logs = run_shell("logcat -d -t 200")
        if not logs:
            return False

        pkg_low = pkg.lower()
        for line in logs.splitlines():
            low = line.lower()
            if "279" not in low:
                continue
            if not any(k in low for k in ("error", "disconnect", "connection", "kick")):
                continue
            parts = line.split()
            pid_match = len(parts) >= 3 and parts[2] in pids
            if pid_match or pkg_low in low:
                return True
    except Exception:
        pass
    return False

def _get_pkg_owner(pkg):
    data_dir = f"/data/data/{pkg}"
    owner = run_shell(f"stat -L -c '%u:%g' {shlex.quote(data_dir)}").strip()
    if owner and ":" in owner:
        return owner
    return ""

def _create_fallback_cookies_db(db_path):
    if os.path.exists(db_path):
        os.remove(db_path)
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        cur.execute("PRAGMA journal_mode=DELETE")
        cur.execute(
            "CREATE TABLE meta("
            "key LONGVARCHAR NOT NULL UNIQUE PRIMARY KEY, "
            "value LONGVARCHAR)"
        )
        cur.execute(
            "CREATE TABLE cookies("
            "creation_utc INTEGER NOT NULL,"
            "host_key TEXT NOT NULL,"
            "top_frame_site_key TEXT NOT NULL,"
            "name TEXT NOT NULL,"
            "value TEXT NOT NULL,"
            "encrypted_value BLOB NOT NULL,"
            "path TEXT NOT NULL,"
            "expires_utc INTEGER NOT NULL,"
            "is_secure INTEGER NOT NULL,"
            "is_httponly INTEGER NOT NULL,"
            "last_access_utc INTEGER NOT NULL,"
            "has_expires INTEGER NOT NULL,"
            "is_persistent INTEGER NOT NULL,"
            "priority INTEGER NOT NULL,"
            "samesite INTEGER NOT NULL,"
            "source_scheme INTEGER NOT NULL,"
            "source_port INTEGER NOT NULL,"
            "is_same_party INTEGER NOT NULL,"
            "last_update_utc INTEGER NOT NULL)"
        )
        cur.execute(
            "CREATE UNIQUE INDEX cookies_unique_index "
            "ON cookies(host_key, top_frame_site_key, name, path)"
        )
        cur.executemany(
            "INSERT INTO meta(key, value) VALUES (?, ?)",
            [("mmap_status", "-1"), ("version", "18"), ("last_compatible_version", "18")],
        )
        con.commit()
    finally:
        con.close()

def _has_cookies_table(db_path):
    if not os.path.isfile(db_path) or os.path.getsize(db_path) < 1024:
        return False
    con = None
    try:
        con = sqlite3.connect(db_path)
        row = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='cookies'"
        ).fetchone()
        return row is not None
    except Exception:
        return False
    finally:
        if con is not None:
            con.close()

def _read_roblosecurity_from_db(db_path):
    if not _has_cookies_table(db_path):
        return None
    con = None
    try:
        con = sqlite3.connect(db_path)
        row = con.execute(
            "SELECT value FROM cookies WHERE name = '.ROBLOSECURITY' "
            "AND host_key IN ('.roblox.com', 'roblox.com', 'www.roblox.com') "
            "ORDER BY last_update_utc DESC LIMIT 1"
        ).fetchone()
        return row[0] if row and row[0] else None
    except Exception:
        try:
            row = con.execute(
                "SELECT value FROM cookies WHERE name = '.ROBLOSECURITY' LIMIT 1"
            ).fetchone()
            return row[0] if row and row[0] else None
        except Exception:
            return None
    finally:
        if con is not None:
            con.close()

def _upsert_roblosecurity_in_db(db_path, cookie):
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        cur.execute("PRAGMA journal_mode=DELETE")
        col_info = list(cur.execute("PRAGMA table_info(cookies)"))
        if not col_info:
            raise RuntimeError("cookies table has no columns")

        now_us = int((time.time() + CHROME_EPOCH_OFFSET) * 1_000_000)
        max_row = cur.execute("SELECT MAX(creation_utc) FROM cookies").fetchone()
        if max_row and max_row[0] is not None and max_row[0] >= now_us:
            now_us = int(max_row[0]) + 1
        exp_us = now_us + COOKIE_TTL_DAYS * 86400 * 1_000_000

        defaults = {
            "creation_utc": now_us,
            "host_key": ".roblox.com",
            "top_frame_site_key": "",
            "name": ".ROBLOSECURITY",
            "value": cookie,
            "encrypted_value": b"",
            "path": "/",
            "expires_utc": exp_us,
            "is_secure": 1,
            "is_httponly": 1,
            "last_access_utc": now_us,
            "has_expires": 1,
            "is_persistent": 1,
            "priority": 1,
            "samesite": -1,
            "source_scheme": 2,
            "source_port": 443,
            "is_same_party": 0,
            "last_update_utc": now_us,
            "source_type": 0,
            "has_cross_site_ancestor": 0,
        }

        cols = []
        vals = []
        for _cid, name, ctype, _notnull, _dflt, _pk in col_info:
            cols.append(name)
            if name in defaults:
                vals.append(defaults[name])
            else:
                ct = (ctype or "").upper()
                if "BLOB" in ct:
                    vals.append(b"")
                elif "CHAR" in ct or "TEXT" in ct or "CLOB" in ct:
                    vals.append("")
                else:
                    vals.append(0)

        cur.execute("DELETE FROM cookies WHERE name = '.ROBLOSECURITY'")
        placeholders = ",".join("?" for _ in cols)
        cur.execute(
            f"INSERT OR REPLACE INTO cookies ({','.join(cols)}) VALUES ({placeholders})",
            vals,
        )
        con.commit()

        check = cur.execute("PRAGMA integrity_check").fetchone()
        if not check or check[0].lower() != "ok":
            raise RuntimeError(f"sqlite integrity_check failed: {check}")

        verify = cur.execute(
            "SELECT value FROM cookies WHERE name = '.ROBLOSECURITY' AND host_key = '.roblox.com'"
        ).fetchone()
        if not verify or verify[0] != cookie:
            raise RuntimeError("injected cookie verification mismatch")
    finally:
        con.close()

def _strip_prefs_user_keys(xml_text):
    keys_pat = "|".join(re.escape(k) for k in ROBLOX_PREFS_USER_KEYS)
    pattern = (
        r'^[ \t]*<(?:string|long|int|boolean)\s+name="(?:'
        + keys_pat
        + r')"[^>]*?(?:/>|>.*?</(?:string|long|int|boolean)>)[ \t]*\r?\n?'
    )
    return re.sub(pattern, "", xml_text, flags=re.MULTILINE | re.DOTALL)

def _pull_file_as_root(src_path, dst_path):
    uid_gid = f"{os.getuid()}:{os.getgid()}" if hasattr(os, "getuid") else "0:0"
    q_src = shlex.quote(src_path)
    q_dst = shlex.quote(dst_path)
    cmd = f"if [ -f {q_src} ]; then cat {q_src} > {q_dst} && chown {uid_gid} {q_dst} && chmod 600 {q_dst}; fi"
    exec_shell(cmd)
    return os.path.isfile(dst_path)

def _pull_cookies_bundle(pkg, tmp_dir):
    base = f"/data/data/{pkg}/app_webview/Default"
    tmp_db = os.path.join(tmp_dir, "Cookies")
    for suffix in ("", "-journal", "-wal", "-shm"):
        p = os.path.join(tmp_dir, "Cookies" + suffix)
        if os.path.exists(p):
            os.remove(p)
        _pull_file_as_root(f"{base}/Cookies{suffix}", p)
    return tmp_db

def _bootstrap_webview_cookies(pkg, cookies_path):
    q_pkg = shlex.quote(pkg)
    q_ck = shlex.quote(cookies_path)
    exec_shell(f"rm -f {q_ck} {q_ck}-journal {q_ck}-wal {q_ck}-shm")

    act = run_shell(f"cmd package resolve-activity --brief {q_pkg}").splitlines()
    component = act[-1].strip() if act else ""
    if "/" in component and not component.lower().startswith("no "):
        exec_shell(f"am start -n {shlex.quote(component)}")
    else:
        exec_shell(f"monkey -p {q_pkg} -c android.intent.category.LAUNCHER 1")

    for _ in range(8):
        time.sleep(1.0)
        sz = run_shell(f"stat -c '%s' {q_ck}").strip()
        if sz.isdigit() and int(sz) >= 4096:
            break

    exec_shell(f"am force-stop {q_pkg}")
    time.sleep(1.0)

def _clean_stale_session_files(pkg, owner, tmp_dir):
    base = f"/data/data/{pkg}"
    q_def = shlex.quote(f"{base}/app_webview/Default")
    q_app_storage = shlex.quote(f"{base}/files/appData/LocalStorage/appStorage.json")
    q_db_dir = shlex.quote(f"{base}/databases")

    exec_shell(
        f"rm -f {q_def}/Cookies-journal {q_def}/Cookies-wal {q_def}/Cookies-shm "
        f"{q_app_storage} {q_db_dir}/roblox-database-default*"
    )

    prefs_path = f"{base}/shared_prefs/prefs.xml"
    tmp_prefs = os.path.join(tmp_dir, "prefs.xml")
    if _pull_file_as_root(prefs_path, tmp_prefs):
        try:
            with open(tmp_prefs, "r", encoding="utf-8", errors="ignore") as f:
                orig_xml = f.read()
            cleaned_xml = _strip_prefs_user_keys(orig_xml)
            if cleaned_xml != orig_xml:
                with open(tmp_prefs, "w", encoding="utf-8") as f:
                    f.write(cleaned_xml)
                q_tmp = shlex.quote(tmp_prefs)
                q_prefs = shlex.quote(prefs_path)
                q_own = shlex.quote(owner)
                exec_shell(
                    f"cat {q_tmp} > {q_prefs} && chown {q_own} {q_prefs} && "
                    f"chmod 660 {q_prefs} && (restorecon {q_prefs} 2>/dev/null || true)"
                )
        except Exception:
            pass

def is_session_synced(pkg, expected_uid, expected_cookie):
    if not HAS_ROOT or not pkg or not expected_cookie:
        return False
    ck = normalize_cookie(expected_cookie)
    if not ck:
        return False

    if expected_uid:
        prefs_path = f"/data/data/{pkg}/shared_prefs/prefs.xml"
        uid_line = run_shell(
            f"grep -F 'name=\"userid_long\"' {shlex.quote(prefs_path)}"
        )
        if f'value="{expected_uid}"' not in uid_line:
            return False

    tmp_dir = tempfile.mkdtemp(prefix="rblx_chk_")
    try:
        tmp_db = _pull_cookies_bundle(pkg, tmp_dir)
        stored_ck = _read_roblosecurity_from_db(tmp_db)
        return stored_ck == ck
    except Exception:
        return False
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

def inject_cookie_to_pkg(pkg, cookie):
    if not HAS_ROOT:
        return False, "Root (su) access is required to inject cookies"
    ck = normalize_cookie(cookie)
    if not pkg or not ck:
        return False, "Invalid package or empty cookie"

    q_pkg = shlex.quote(pkg)
    if run_shell(f"pidof {q_pkg}").strip():
        exec_shell(f"am force-stop {q_pkg}")
        time.sleep(1.0)

    owner = _get_pkg_owner(pkg)
    if not owner:
        return False, f"Package data directory not found: /data/data/{pkg}"

    webview_dir = f"/data/data/{pkg}/app_webview"
    default_dir = f"{webview_dir}/Default"
    cookies_path = f"{default_dir}/Cookies"

    tmp_dir = tempfile.mkdtemp(prefix="rblx_ck_")
    try:
        tmp_db = _pull_cookies_bundle(pkg, tmp_dir)
        if not _has_cookies_table(tmp_db):
            _bootstrap_webview_cookies(pkg, cookies_path)
            tmp_db = _pull_cookies_bundle(pkg, tmp_dir)
        if not _has_cookies_table(tmp_db):
            _create_fallback_cookies_db(tmp_db)

        _upsert_roblosecurity_in_db(tmp_db, ck)
        expected_size = os.path.getsize(tmp_db)

        _clean_stale_session_files(pkg, owner, tmp_dir)

        q_wv = shlex.quote(webview_dir)
        q_def = shlex.quote(default_dir)
        q_dst = shlex.quote(cookies_path)
        q_tmp = shlex.quote(tmp_db)
        q_own = shlex.quote(owner)

        push_cmd = (
            f"mkdir -p {q_def} && "
            f"cat {q_tmp} > {q_dst} && "
            f"chown {q_own} {q_wv} {q_def} {q_dst} && "
            f"chmod 770 {q_wv} {q_def} && "
            f"chmod 660 {q_dst} && "
            f"(restorecon -R {q_wv} 2>/dev/null || true)"
        )
        rc = exec_shell(push_cmd)
        if rc != 0:
            return False, f"Failed to write Cookies DB to {cookies_path}"

        actual_size = run_shell(f"stat -c '%s' {q_dst}").strip()
        if not actual_size.isdigit() or int(actual_size) != expected_size:
            return False, f"Cookies DB size mismatch (expected {expected_size}, got {actual_size or 'none'})"

        return True, "OK"
    except Exception as e:
        return False, str(e)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

def launch_and_join_single_tab(pkg, game_id, acc_info=None, is_rejoin=False, force_inject=False):
    """Khởi động từng tab riêng lẻ và cho join thẳng vào Game ID đã set ngay lập tức."""
    display_name = acc_info["name"] if acc_info else "Chưa gắn Cookie"
    action_text = "REJOIN & JOIN GAME" if is_rejoin else "KHỞI ĐỘNG & JOIN GAME"
    print(f"\n{C_YELLOW}{C_BOLD}  [⏳] {action_text}: {pkg}{C_RESET}")
    print(f"       {C_WHITE}• Tài khoản : {C_PURPLE}{display_name}{C_RESET}")
    print(f"       {C_WHITE}• ID Game   : {C_GREEN}{game_id}{C_RESET}")

    q_pkg = shlex.quote(pkg)
    exec_shell(f"am force-stop {q_pkg}")
    time.sleep(1.2)

    if acc_info and acc_info.get("cookie"):
        cookie = normalize_cookie(acc_info["cookie"])
        need_inject = force_inject or not is_session_synced(pkg, acc_info.get("uid"), cookie)
        if need_inject:
            ok, err = inject_cookie_to_pkg(pkg, cookie)
            if not ok:
                print(f"{C_RED}{C_BOLD}  [ERROR] Cookie inject failed for {pkg}: {err}{C_RESET}")
                return False
            print(f"{C_GREEN}  [OK] Injected WebView SQLite cookie for {pkg}{C_RESET}")
        else:
            print(f"{C_DIM}  [OK] Existing session already synced for {pkg}{C_RESET}")

    url_direct = f"roblox://placeId={game_id}"
    rc = exec_shell(f"am start -p {q_pkg} -a android.intent.action.VIEW -d {shlex.quote(url_direct)}")
    if rc != 0:
        print(f"{C_RED}{C_BOLD}  [ERROR] Failed to launch {pkg} with placeId={game_id}{C_RESET}")
        return False

    print(f"{C_GREEN}{C_BOLD}  [✔] Đã khởi động tab {pkg} & join thẳng vào Game ID {game_id}!{C_RESET}")
    return True

def kill_and_rejoin_pkg(pkg, game_id, acc_info=None, reason="Mất kết nối"):
    """Kill đúng tab đang lỗi và rejoin lại tab đó vào Game ID ngay."""
    display_name = acc_info["name"] if acc_info else pkg
    print(f"\n{C_RED}{C_BOLD}  [🛑 KILL & REJOIN] {display_name} ({pkg}) -> Lý do: {reason}{C_RESET}")
    return launch_and_join_single_tab(pkg, game_id, acc_info, is_rejoin=True, force_inject=False)

def launch_package_tab(pkg, game_id, acc_info=None, is_rejoin=False, force_inject=False):
    return launch_and_join_single_tab(pkg, game_id, acc_info, is_rejoin=is_rejoin, force_inject=force_inject)

def run_auto_rejoin(cfg):
    active_pkgs = [p["pkg"] for p in cfg.get("packages", []) if p.get("active", True)]
    if not active_pkgs:
        print(f"\n{C_RED}{C_BOLD}  [!] BẠN CHƯA CHỌN PACKAGE NÀO ĐỂ CHẠY!{C_RESET}")
        print(f"{C_YELLOW}  ➔ Hãy vào mục [2] để BẬT các Package cần chạy trên CloudPhone.{C_RESET}")
        time.sleep(3)
        return

    acc_map = {a["pkg"]: a for a in cfg.get("accounts", [])}
    last_launch = {}
    grace_sec = max(LAUNCH_GRACE_SECONDS, cfg.get("delay", 20))

    os.system("clear")
    print(f"{C_CYAN}{C_BOLD}╔════════════════════════════════════════════════════════════════════════════╗{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}║                 🚀 HỆ THỐNG AUTO-REJOIN ĐANG HOẠT ĐỘNG 🚀                  ║{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}╚════════════════════════════════════════════════════════════════════════════╝{C_RESET}\n")
    print(f"  {C_YELLOW}{C_BOLD}• ID GAME MỤC TIÊU   :{C_RESET} {C_GREEN}{C_BOLD}{cfg['game_id']}{C_RESET}")
    print(f"  {C_YELLOW}{C_BOLD}• SỐ PACKAGE ĐÃ CHỌN :{C_RESET} {C_WHITE}{C_BOLD}{len(active_pkgs)} tab đang kích hoạt{C_RESET}")
    print(f"  {C_YELLOW}{C_BOLD}• CHU KỲ KIỂM TRA    :{C_RESET} {C_WHITE}{C_BOLD}{cfg.get('delay', 20)} giây / lần{C_RESET}\n")
    print(f"{C_CYAN}──────────────────────────────────────────────────────────────────────────────{C_RESET}")

    # Khởi động từng tab và cho join thẳng vào game ngay (không đợi mở hết các tab)
    print(f"\n{C_PURPLE}{C_BOLD}  [⚡] KHỞI ĐỘNG TỪNG TAB & JOIN GAME NGAY (TRÁNH CRASH ĐỒNG LOẠT)...{C_RESET}")
    for pkg in active_pkgs:
        launch_and_join_single_tab(pkg, cfg["game_id"], acc_map.get(pkg), is_rejoin=False)
        last_launch[pkg] = time.time()
        time.sleep(5)

    print(f"\n{C_GREEN}{C_BOLD}  [⚡] ĐÃ KHỞI ĐỘNG & GỬI JOIN TỪNG TAB! BẮT ĐẦU GIÁM SÁT (BAO GỒM ERROR 279)...{C_RESET}")
    print(f"{C_YELLOW}  (Nhấn tổ hợp phím Ctrl + C để dừng và quay về Menu chính){C_RESET}\n")

    try:
        while True:
            print(f"{C_DIM}──────────────────────────────────────────────────────────────────────────────{C_RESET}")
            print(f"{C_CYAN}{C_BOLD}  [⏰ KIỂM TRA LÚC: {time.strftime('%H:%M:%S')}]{C_RESET}\n")
            for pkg in active_pkgs:
                acc = acc_map.get(pkg)
                pid = run_shell(f"pidof {shlex.quote(pkg)}").strip()
                err279 = has_error_279(pkg, pid)
                elapsed = time.time() - last_launch.get(pkg, 0)
                in_grace = elapsed < grace_sec

                if acc and acc.get("uid"):
                    if err279 or (not pid and elapsed >= 8):
                        reason = "Phát hiện lỗi Error 279 (Mất kết nối)" if err279 else "Tiến trình App đã tắt"
                        kill_and_rejoin_pkg(pkg, cfg["game_id"], acc, reason=reason)
                        last_launch[pkg] = time.time()
                        time.sleep(6)
                        continue

                    ingame = is_in_game(acc["uid"], acc.get("cookie"))
                    if ingame is True:
                        print(f"{C_GREEN}{C_BOLD}  [✔ ONLINE] {acc['name']:<18} | {pkg} -> Giữ nguyên tab, đang cày ổn định{C_RESET}")
                    elif in_grace:
                        remain = int(max(0, grace_sec - elapsed))
                        print(f"{C_YELLOW}  [BOOTING] {acc['name']:<18} | {pkg} -> Waiting for game join ({remain}s grace left){C_RESET}")
                    elif ingame is None:
                        print(f"{C_YELLOW}  [WARN] {acc['name']:<18} | {pkg} -> Presence API unavailable, keeping running tab{C_RESET}")
                    else:
                        kill_and_rejoin_pkg(pkg, cfg["game_id"], acc, reason="Bị văng khỏi phòng / Mất kết nối")
                        last_launch[pkg] = time.time()
                        time.sleep(6)
                else:
                    if err279 or (not pid and elapsed >= 8):
                        reason = "Phát hiện lỗi Error 279" if err279 else "Tiến trình App đã tắt"
                        kill_and_rejoin_pkg(pkg, cfg["game_id"], None, reason=reason)
                        last_launch[pkg] = time.time()
                        time.sleep(6)
                    else:
                        print(f"{C_GREEN}{C_BOLD}  [✔ RUNNING] {pkg} (PID: {pid}) -> Giữ nguyên tab, App đang chạy ổn định{C_RESET}")

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
    mode_label = "ROOT (su)" if HAS_ROOT else "NON-ROOT"
    
    print(f"{C_CYAN}{C_BOLD}╔════════════════════════════════════════════════════════════════════════════╗{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}║                                                                            ║{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}║               TUE GAY               ║{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}║                                                                            ║{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}╠════════════════════════════════════════════════════════════════════════════╣{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}║                                                                            ║{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}║{C_RESET}   {C_YELLOW}{C_BOLD}• ID GAME MỤC TIÊU     :{C_RESET}  {C_GREEN}{C_BOLD}{cfg['game_id']:<47}{C_RESET}{C_CYAN}{C_BOLD}║{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}║{C_RESET}   {C_YELLOW}{C_BOLD}• HIỆU SUẤT THIẾT BỊ   :{C_RESET}  {C_PURPLE}{C_BOLD}{f'CPU: {cpu_usage}  |  RAM: {ram_usage}  [{mode_label}]':<47}{C_RESET}{C_CYAN}{C_BOLD}║{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}║{C_RESET}   {C_YELLOW}{C_BOLD}• PACKAGE CLOUDPHONE   :{C_RESET}  {C_WHITE}{C_BOLD}{f'{active_count} đang BẬT  /  {len(pkgs_list)} đã lưu':<47}{C_RESET}{C_CYAN}{C_BOLD}║{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}║{C_RESET}   {C_YELLOW}{C_BOLD}• TÀI KHOẢN COOKIE     :{C_RESET}  {C_WHITE}{C_BOLD}{str(len(cfg['accounts'])) + ' tài khoản đã liên kết':<47}{C_RESET}{C_CYAN}{C_BOLD}║{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}║                                                                            ║{C_RESET}")
    print(f"{C_CYAN}{C_BOLD}╚════════════════════════════════════════════════════════════════════════════╝{C_RESET}")
    
    print(f"\n{C_CYAN}{C_BOLD}   ══════════════════════════[ BẢNG ĐIỀU KHIỂN CHÍNH ]══════════════════════════{C_RESET}\n")
    print(f"      {C_GREEN}{C_BOLD}[1]{C_RESET}   🚀   {C_WHITE}{C_BOLD}KHỞI ĐỘNG TẤT CẢ TAB ĐÃ SET & CHẠY AUTO-REJOIN{C_RESET}\n")
    print(f"      {C_GREEN}{C_BOLD}[2]{C_RESET}   📦   {C_WHITE}{C_BOLD}SET PACKAGE & CHỌN PACKAGE CHẠY TRÊN CLOUDPHONE{C_RESET}\n")
    print(f"      {C_GREEN}{C_BOLD}[3]{C_RESET}   🍪   {C_WHITE}{C_BOLD}NHẬP NHIỀU COOKIE HÀNG LOẠT & TỰ ĐỘNG LOGIN VÀO PACKAGE{C_RESET}\n")
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
            print(f"     {C_GREEN}{C_BOLD}[A]{C_RESET}  Quét tất cả Client (Delta, Arceus, Noka, Clone...) trên máy\n")
            print(f"     {C_GREEN}{C_BOLD}[D]{C_RESET}  Hiển thị TOÀN BỘ ứng dụng trên máy\n")
            print(f"     {C_GREEN}{C_BOLD}[B]{C_RESET}  Bật TẤT CẢ Package      |      {C_RED}{C_BOLD}[C]{C_RESET}  Tắt TẤT CẢ Package\n")
            print(f"     {C_YELLOW}{C_BOLD}[Số STT]{C_RESET}  Nhập số (vd: 1 hoặc 1,2) để Bật/Tắt nhanh      |      {C_RED}{C_BOLD}[0]{C_RESET}  Quay lại\n")
            
            sub = input(f"\n{C_CYAN}{C_BOLD}  ➜ NHẬP LỰA CHỌN CỦA BẠN: {C_RESET}").strip()
            if sub == "0":
                break
            elif sub.upper() in ["A", "D"]:
                detected = scan_packages() if sub.upper() == "A" else sorted([p.replace("package:", "").strip() for p in run_shell("pm list packages -3").splitlines() if p.strip()])
                
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
        print(f"{C_CYAN}{C_BOLD}║              NHẬP HÀNG LOẠT COOKIE & TỰ ĐỘNG LOGIN VÀO APP                 ║{C_RESET}")
        print(f"{C_CYAN}{C_BOLD}╚════════════════════════════════════════════════════════════════════════════╝{C_RESET}\n")
        if not HAS_ROOT:
            print(f"{C_RED}{C_BOLD}  [ERROR] Root (su) is required to inject cookies into Roblox WebView DB.{C_RESET}\n")
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
        print(f"  {C_YELLOW}HƯỚNG DẪN NHẬP & LOGIN TỰ ĐỘNG:{C_RESET}")
        print(f"  - Dán danh sách nhiều Cookie (mỗi dòng 1 cookie).")
        print(f"  - Tool sẽ tự động gán vào Package và khởi động app để login ngay.\n")
        
        print(f"{C_CYAN}{C_BOLD}  ➔ Dán danh sách Cookie (Gõ 'END' ở dòng cuối để kết thúc):{C_RESET}")
        
        lines = []
        while True:
            try:
                line = input()
                if line.strip().upper() == "END":
                    break
                if not line.strip():
                    if lines:
                        break
                    continue
                lines.append(line.strip())
            except EOFError:
                break
                
        raw_cookies = []
        for l in lines:
            if "_|WARNING" in l or ".ROBLOSECURITY" in l or len(l) > 50:
                raw_cookies.append(l)

        if not raw_cookies:
            raw_cookies = [c.strip() for c in "".join(lines).split() if len(c) > 50]

        print(f"\n{C_YELLOW}  [⏳] Đang xác thực {len(raw_cookies)} Cookie và tiến hành Login hàng loạt...{C_RESET}")
        
        success_count = 0
        for idx, raw_ck in enumerate(raw_cookies):
            if idx >= len(saved_pkgs):
                print(f"{C_RED}  [!] Số lượng cookie vượt quá số Package hiện có!{C_RESET}")
                break
            target_pkg = saved_pkgs[idx]["pkg"]
            uid, uname, valid_ck = verify_cookie(raw_ck)
            if uid:
                cfg["accounts"] = [a for a in cfg["accounts"] if a["pkg"] != target_pkg]
                new_acc = {"name": uname, "uid": uid, "pkg": target_pkg, "cookie": valid_ck}
                cfg["accounts"].append(new_acc)
                save_cfg(cfg)
                
                print(f"  {C_GREEN}[✔] Gắn thành công: {C_PURPLE}{uname}{C_GREEN} ➔ {target_pkg}{C_RESET}")
                launched = launch_package_tab(
                    target_pkg, cfg["game_id"], new_acc, is_rejoin=False, force_inject=True
                )
                if launched:
                    success_count += 1
                time.sleep(4)
            else:
                print(f"  {C_RED}[✖] Cookie thứ {idx+1} không hợp lệ hoặc đã chết, bỏ qua.{C_RESET}")
                
        save_cfg(cfg)
        print(f"\n{C_GREEN}{C_BOLD}  [✔ HOÀN TẤT] Đã gán và khởi động thành công {success_count} tài khoản!{C_RESET}")
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
            exec_shell(f"am force-stop {shlex.quote(item['pkg'])}")
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
                pid = run_shell(f"pidof {shlex.quote(pkg)}").strip()
                
                mode_str = f"{C_GREEN}{C_BOLD}✔ BẬT CHẠY{C_RESET}" if is_active else f"{C_RED}{C_BOLD}✖ ĐANG TẮT{C_RESET}"
                app_str = f"{C_GREEN}{C_BOLD}ĐANG MỞ (PID: {pid}){C_RESET}" if pid else f"{C_RED}{C_BOLD}ĐÃ ĐÓNG (OFFLINE){C_RESET}"
                
                if acc:
                    ig = is_in_game(acc["uid"], acc.get("cookie"))
                    acc_str = f"{C_PURPLE}{C_BOLD}{acc['name']}{C_RESET} (ID: {acc['uid']})"
                    if ig is True:
                        game_str = f"{C_GREEN}{C_BOLD}🎮 ĐANG TRONG GAME (IN-GAME){C_RESET}"
                    elif ig is None:
                        game_str = f"{C_YELLOW}{C_BOLD}[WARN] Presence API unavailable{C_RESET}"
                    else:
                        game_str = f"{C_RED}{C_BOLD}❌ MẤT KẾT NỐI / NGOÀI SẢNH{C_RESET}"
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
        print(f"{C_CYAN}{C_BOLD}Hẹn gặp lại bạn!{C_RES... (Còn 1 KB)
