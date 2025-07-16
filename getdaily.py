#!/usr/bin/env python3
import requests
from pathlib import Path

# Lokasi file konfigurasi & cache
DAYLIDATA = Path.home() / "daylidata.txt"
PROXY_CACHE_FILE = Path("proxy_ok.txt")
FILE_NAME = "TESSTSS7.txt"
session = requests.Session()

def load_config(path):
    config = {}
    try:
        with open(path) as f:
            code = f.read()
        exec(code, {}, config)
        return config
    except Exception as e:
        print(f"[!] Gagal membaca konfigurasi: {e}")
        return {}

def get_proxies(proxy_url):
    try:
        res = requests.get(proxy_url, timeout=10)
        res.raise_for_status()
        return res.text.strip().splitlines()
    except Exception as e:
        print(f"[!] Gagal ambil proxy list: {e}")
        return []

def load_cached_proxy():
    if PROXY_CACHE_FILE.exists():
        with open(PROXY_CACHE_FILE) as f:
            return f.read().strip()
    return None

def save_working_proxy(proxy):
    with open(PROXY_CACHE_FILE, "w") as f:
        f.write(proxy.strip())

def try_proxy(proxy, dailymotion_url, meta_url_template):
    proxies = {"http": proxy, "https": proxy}
    try:
        print(f"[•] Coba proxy: {proxy}")

        video_id = dailymotion_url.split('/video/')[1].split('_')[0]
        meta_url = meta_url_template.format(video_id=video_id)

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://sevenhub.id/",
            "Origin": "https://sevenhub.id"
        }

        res = session.get(meta_url, headers=headers, proxies=proxies, timeout=10)
        res.raise_for_status()
        meta = res.json()

        qualities = meta.get("qualities", {})
        if not qualities:
            print("[!] Tidak ada kualitas video")
            return False

        # Ambil kualitas tertinggi numerik
        numeric_qualities = [
            (int(q), qualities[q][0]["url"])
            for q in qualities
            if q.isdigit() and qualities[q]
        ]

        if not numeric_qualities:
            print("[!] Tidak menemukan kualitas numerik")
            return False

        best_quality_url = max(numeric_qualities, key=lambda x: x[0])[1]
        print(f"[✓] Dapat URL kualitas tertinggi: {best_quality_url}")

        with open(FILE_NAME, "w") as f:
            f.write(best_quality_url + "\n")

        print(f"[✓] Simpan URL ke {FILE_NAME}")
        save_working_proxy(proxy)
        return True

    except Exception as e:
        print(f"[×] Gagal proxy {proxy}: {e}")
        return False
        
def fallback_write(fallback_url):
    try:
        print(f"[!] Menggunakan fallback: {fallback_url}")
        res = session.get(fallback_url, timeout=10)
        res.raise_for_status()
        with open(FILE_NAME, "w") as f:
            f.write(res.text)
        print(f"[✓] Fallback disimpan ke {FILE_NAME}")

        # Tambahkan agar file cache tetap ada
        if not PROXY_CACHE_FILE.exists():
            PROXY_CACHE_FILE.write_text("#fallback-used")

    except Exception as e:
        print(f"[×] Gagal ambil fallback: {e}")
        
def main():
    if not DAYLIDATA.exists():
        print(f"[!] File {DAYLIDATA} tidak ditemukan.")
        return

    config = load_config(DAYLIDATA)
    if not config:
        print("❌ Konfigurasi tidak valid.")
        return

    DAILYMOTION_URL = config.get("DAILYMOTION_URL")
    FALLBACK_URL = config.get("FALLBACK_URL")
    url_proxy = config.get("url_proxy")
    meta_url = config.get("meta_url")

    if not all([DAILYMOTION_URL, FALLBACK_URL, url_proxy, meta_url]):
        print("❌ Ada parameter yang belum lengkap di daylidata.txt")
        return

    # 1. Coba proxy cache dulu
    cached_proxy = load_cached_proxy()
    if cached_proxy:
        print(f"[•] Coba proxy cache terlebih dahulu: {cached_proxy}")
        if try_proxy(cached_proxy, DAILYMOTION_URL, meta_url):
            print("✅ Berhasil dengan proxy cache")
            return
        else:
            print("✖️ Proxy cache gagal, lanjut ke daftar proxy")

    # 2. Coba daftar proxy
    proxies = get_proxies(url_proxy)
    if not proxies:
        print("❌ Tidak ada proxy tersedia")
        fallback_write(FALLBACK_URL)
        return

    for proxy in proxies:
        if try_proxy(proxy, DAILYMOTION_URL, meta_url):
            print("✅ Berhasil ambil m3u8")
            return

    print("❌ Semua proxy gagal")
    fallback_write(FALLBACK_URL)

if __name__ == "__main__":
    main()
