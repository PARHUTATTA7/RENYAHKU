import sys
import requests
from pathlib import Path


# Load konfigurasi
CONFIG = {}
exec((Path.home() / "datamdtv_file.txt").read_text(encoding="utf-8"), CONFIG)


CHANNEL_ID = CONFIG["CHANNEL_ID"]
API_URL = CONFIG["API_URL"]
PROXY_LIST_URL = CONFIG["PROXY_LIST_URL"]
HEADERS = CONFIG["HEADERS"]


def get_proxy_list(url):
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        return [
            p.strip()
            for p in res.text.splitlines()
            if p.strip() and not p.startswith("#")
        ]
    except Exception as e:
        print(f"[!] Gagal ambil proxy list: {e}", file=sys.stderr)
        return []


def build_proxies(proxy):
    port = proxy.rsplit(":", 1)[1]

    # Port yang biasanya SOCKS
    if port in ("1080", "4145", "5430", "5678"):
        scheme = "socks5://"
    else:
        scheme = "http://"

    return {
        "http": scheme + proxy,
        "https": scheme + proxy,
    }

def try_proxy(api_url, proxy, headers):
    proxies = build_proxies(proxy)

    try:
        print(f"[•] {proxy}", file=sys.stderr)

        r = requests.get(
            api_url,
            headers=headers,
            proxies=proxies,
            timeout=5,
        )

        r.raise_for_status()
        return r.json()

    except Exception as e:
        print(f"[×] {proxy} -> {e}", file=sys.stderr)
        return None


def direct_request(api_url, headers):
    try:
        print("[•] Mencoba koneksi langsung...", file=sys.stderr)

        res = requests.get(
            api_url,
            headers=headers,
            timeout=10,
        )

        res.raise_for_status()
        return res.json()

    except Exception as e:
        print(f"[×] Direct gagal: {e}", file=sys.stderr)
        return None


def main():
    data = None

    proxy_list = get_proxy_list(PROXY_LIST_URL)

    print(f"[+] Total proxy: {len(proxy_list)}", file=sys.stderr)

    for proxy in proxy_list:
        data = try_proxy(API_URL, proxy, HEADERS)

        if data and data.get("success"):
            print(f"[✓] Berhasil memakai proxy: {proxy}", file=sys.stderr)
            break

    if data is None:
        data = direct_request(API_URL, HEADERS)

    if not data:
        print("Tidak dapat mengambil data.", file=sys.stderr)
        return

    if not data.get("success") or not data.get("data"):
        print(data, file=sys.stderr)
        return

    stream = data["data"].get("url_streaming")
    sign = data["data"].get("sign_url")

    if not stream or not sign:
        print("Stream URL tidak ditemukan.", file=sys.stderr)
        return

    final_url = stream + ("&" if "?" in stream else "?") + sign

    with open("mdtv.m3u8.txt", "w", encoding="utf-8") as f:
        f.write(final_url)

    print(final_url)


if __name__ == "__main__":
    main()
