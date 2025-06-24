import requests
from pathlib import Path
import time

DATATESTER = Path.home() / "datatester.txt"
PROXY_FILE = Path("proxy_tester_list.txt")
TEST_TIMEOUT = 5
MAX_VALID = 5

def load_config(file_path):
    config = {}
    if not file_path.exists():
        print(f"[!] File konfigurasi tidak ditemukan: {file_path}")
        return None

    try:
        exec(file_path.read_text(), {}, config)
        return config
    except Exception as e:
        print(f"[!] Gagal parsing datatester.txt: {e}")
        return None

def fetch_proxy_list(proxy_source):
    try:
        r = requests.get(proxy_source, timeout=10)
        r.raise_for_status()
        return r.text.strip().splitlines()
    except Exception as e:
        print(f"[!] Gagal ambil proxy list: {e}")
        return []

def test_proxy(proxy, test_url, headers):
    proxies = {"http": proxy, "https": proxy}
    try:
        r = requests.get(test_url, headers=headers, proxies=proxies, timeout=TEST_TIMEOUT)
        if r.status_code == 200:
            print(f"[✓] Valid: {proxy}")
            return True
    except Exception:
        pass
    print(f"[×] Gagal: {proxy}")
    return False

def save_valid_proxies(valids):
    with open(PROXY_FILE, "w") as f:
        for proxy in valids[:MAX_VALID]:
            f.write(proxy + "\n")
    print(f"[✓] Simpan {len(valids[:MAX_VALID])} proxy ke {PROXY_FILE}")

def main():
    config = load_config(DATATESTER)
    if not config:
        return

    proxy_source = config.get("PROXY_SOURCE")
    test_url = config.get("TEST_URL")
    headers = config.get("HEADERS")

    if not all([proxy_source, test_url, headers]):
        print("❌ Konfigurasi tidak lengkap di datatester.txt.")
        return

    proxies = fetch_proxy_list(proxy_source)
    valids = []

    for proxy in proxies:
        if test_proxy(proxy, test_url, headers):
            valids.append(proxy)
        if len(valids) >= MAX_VALID:
            break
        time.sleep(0.5)

    if valids:
        save_valid_proxies(valids)
    else:
        print("❌ Tidak ada proxy yang valid.")

if __name__ == "__main__":
    main()
