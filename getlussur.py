import requests
import os
import json
import time
import random
import sys
from pathlib import Path

# === Konfigurasi Awal ===
mapping_file = Path.home() / "gasbro_mapping.txt"
CACHE_FILE = Path("proxy_cache.txt")
FAILED_FILE = Path("proxy_failed.txt")

HEADERS = {}
COOKIES = {}
CHANNELS = {}
TEMPLATES = {}
PROXY_LIST_URL = ""

# === Parsing File Mapping ===
def parse_mapping_file(path):
    global PROXY_LIST_URL
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("HEADERS."):
                key, value = line.split("=", 1)
                HEADERS[key.split("HEADERS.")[1]] = value
            elif line.startswith("COOKIES."):
                key, value = line.split("=", 1)
                COOKIES[key.split("COOKIES.")[1]] = value
            elif line.startswith("channels."):
                key, value = line.split("=", 1)
                CHANNELS[key.split("channels.")[1]] = value
            elif line.startswith("TEMPLATE."):
                key, value = line.split("=", 1)
                TEMPLATES[key.split("TEMPLATE.")[1]] = value
            elif line.startswith("PROXY_LIST_URL="):
                PROXY_LIST_URL = line.split("=", 1)[1]

# === Ambil Daftar Proxy ===
def get_proxy_list():
    try:
        res = requests.get(PROXY_LIST_URL, timeout=10)
        res.raise_for_status()
        return res.text.strip().splitlines()
    except Exception as e:
        print(f"[!] Gagal ambil proxy list: {e}", file=sys.stderr)
        return []

# === Coba Request dengan Proxy ===
def try_fetch_with_proxy(proxy, url, headers, cookies):
    proxies = {"http": proxy, "https": proxy}
    try:
        response = requests.post(url, headers=headers, cookies=cookies, proxies=proxies, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[×] Gagal proxy {proxy}: {e}", file=sys.stderr)
        return None

# === Ambil URL Stream untuk Satu Channel ===
def get_vidio_stream(channel_id, channel_name):
    token_template = TEMPLATES.get("token_url")
    if not token_template:
        print(f"[{channel_name}] ❌ TEMPLATE.token_url tidak ditemukan", file=sys.stderr)
        return None

    token_url = token_template.replace("{id}", channel_id).replace("{name}", channel_name)
    headers = {k: v.replace("{id}", channel_id).replace("{name}", channel_name) for k, v in HEADERS.items()}

    proxies = get_proxy_list()
    random.shuffle(proxies)
    tried = set()

    if CACHE_FILE.exists():
        cached = CACHE_FILE.read_text().strip()
        if cached:
            print(f"[•] Coba proxy cache: {cached}", file=sys.stderr)
            data = try_fetch_with_proxy(cached, token_url, headers, COOKIES)
            if data and "hls_url" in data:
                return data["hls_url"]
            tried.add(cached)

    for proxy in proxies:
        if proxy in tried:
            continue
        data = try_fetch_with_proxy(proxy, token_url, headers, COOKIES)
        if data and "hls_url" in data:
            CACHE_FILE.write_text(proxy)
            return data["hls_url"]
        with open(FAILED_FILE, "a") as f:
            f.write(proxy + "\n")
        tried.add(proxy)
        time.sleep(1)

    print(f"[{channel_name}] ❌ Semua proxy gagal.", file=sys.stderr)
    return None

# === Push File ke Repo (dummy fungsi, implementasi GitHub Action) ===
def auto_push_to_repo(filenames):
    print("[✓] File siap di-push:", filenames)

# === Main ===
def main():
    if not mapping_file.exists():
        print("❌ File mapping tidak ditemukan", file=sys.stderr)
        return

    parse_mapping_file(mapping_file)

    written_files = []
    for name, id in CHANNELS.items():
        url = get_vidio_stream(id, name)
        if url:
            filename = f"{name}.m3u8"
            with open(filename, "w") as f:
                f.write(url + "\n")
            written_files.append(filename)
        else:
            print(f"[!] Gagal ambil stream untuk {name}", file=sys.stderr)

    if written_files:
        auto_push_to_repo(written_files)

if __name__ == "__main__":
    main()
