#!/usr/bin/env python3
import subprocess
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
        return PROXY_CACHE_FILE.read_text().strip()
    return None

def save_working_proxy(proxy):
    PROXY_CACHE_FILE.write_text(proxy.strip())

def write_url_to_file(url):
    Path(FILE_NAME).write_text(url + "\n")
    print(f"[✓] URL disimpan ke {FILE_NAME}")

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

        # Pilih kualitas terbaik, numerik jika ada
        numeric = sorted((int(q), q) for q in qualities if q.isdigit())
        best_key = numeric[-1][1] if numeric else sorted(qualities.keys(), reverse=True)[0]
        hls_url = qualities[best_key][0]["url"]

        print(f"[✓] Dapat URL HLS: {hls_url}")
        write_url_to_file(hls_url)
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
        Path(FILE_NAME).write_text(res.text)
        print(f"[✓] Fallback disimpan ke {FILE_NAME}")

        if not PROXY_CACHE_FILE.exists():
            PROXY_CACHE_FILE.write_text("#fallback-used")
    except Exception as e:
        print(f"[×] Gagal ambil fallback: {e}")

def yt_dlp_fetch(dailymotion_url):
    try:
        print("[•] Coba yt-dlp sebagai fallback terakhir...")
        result = subprocess.check_output(
            ["yt-dlp", "-f", "best", "--get-url", dailymotion_url],
            stderr=subprocess.STDOUT,
            text=True
        )
        final_url = result.strip()
        print(f"[✓] yt-dlp URL: {final_url}")
        write_url_to_file(final_url)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[×] yt-dlp gagal: {e.output}")
        return False

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

    # Coba proxy cache dulu
    cached_proxy = load_cached_proxy()
    if cached_proxy:
        print(f"[•] Coba proxy cache terlebih dahulu: {cached_proxy}")
        if try_proxy(cached_proxy, DAILYMOTION_URL, meta_url):
            print("✅ Berhasil dengan proxy cache")
            return
        else:
            print("✖️ Proxy cache gagal, lanjut ke daftar proxy")

    # Coba daftar proxy
    proxies = get_proxies(url_proxy)
    for proxy in proxies:
        if try_proxy(proxy, DAILYMOTION_URL, meta_url):
            print("✅ Berhasil ambil m3u8")
            return

    print("❌ Semua proxy gagal")

    # Fallback: URL statis
    fallback_write(FALLBACK_URL)

    # Terakhir: yt-dlp
    yt_dlp_fetch(DAILYMOTION_URL)

if __name__ == "__main__":
    main()
