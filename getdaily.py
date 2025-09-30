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

def parse_master_playlist(m3u8_url, headers, proxies):
    """Fetch master playlist .m3u8 dan cari variant kualitas tertinggi."""
    try:
        res = session.get(m3u8_url, headers=headers, proxies=proxies, timeout=10)
        res.raise_for_status()
        lines = res.text.splitlines()

        best_url = None
        best_res = 0
        for i, line in enumerate(lines):
            if line.startswith("#EXT-X-STREAM-INF"):
                parts = line.split("RESOLUTION=")
                if len(parts) > 1:
                    res_val = parts[1].split(",")[0]
                    try:
                        w, h = map(int, res_val.split("x"))
                        # pilih yang tinggi (h) terbesar
                        if h > best_res:
                            best_res = h
                            # URL variant ada di baris berikutnya
                            if i + 1 < len(lines):
                                best_url = lines[i + 1]
                    except Exception:
                        pass
        return best_url, best_res
    except Exception as e:
        print(f"[!] Gagal parse master playlist: {e}")
        return None, 0

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

        # Karena live sering hanya “auto”, pakai auto dulu
        if "auto" in qualities:
            hls_master_url = qualities["auto"][0]["url"]
            print(f"[✓] Dapat master playlist (auto): {hls_master_url}")

            # Coba parse master playlist untuk cari variant terbaik
            best_variant_url, best_res = parse_master_playlist(hls_master_url, headers, proxies)
            if best_variant_url:
                print(f"[✓] Variant kualitas tertinggi ({best_res}p): {best_variant_url}")
                final_url = best_variant_url
            else:
                print("[!] Gagal cari variant dari master, fallback ke master")
                final_url = hls_master_url
        else:
            # Kalau JSON ada kualitas numeric (jarang di live), ambil dulu yang tertinggi
            numeric_qualities = [int(q) for q in qualities.keys() if q.isdigit()]
            if numeric_qualities:
                best_quality = str(max(numeric_qualities))
                final_url = qualities[best_quality][0]["url"]
                print(f"[✓] Dapat langsung kualitas {best_quality}p dari API: {final_url}")
            else:
                # fallback ke kualitas apapun yang tersedia
                key_some = list(qualities.keys())[0]
                final_url = qualities[key_some][0]["url"]
                print(f"[✓] Fallback ke kualitas {key_some}: {final_url}")

        # Simpan ke file
        with open(FILE_NAME, "w") as f:
            f.write(final_url + "\n")

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

    # Coba proxy cache dulu
    cached_proxy = load_cached_proxy()
    if cached_proxy:
        print(f"[•] Coba proxy cache terlebih dahulu: {cached_proxy}")
        if try_proxy(cached_proxy, DAILYMOTION_URL, meta_url):
            print("✅ Berhasil dengan proxy cache")
            return
        else:
            print("✖️ Proxy cache gagal, lanjut ke daftar proxy")

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
