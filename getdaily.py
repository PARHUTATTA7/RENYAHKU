#!/usr/bin/env python3
import requests
from pathlib import Path
from urllib.parse import urlparse, parse_qs

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


def build_m3u8_headers(m3u8_url):
    """Bangun header lengkap untuk request master.m3u8"""
    parsed = urlparse(m3u8_url)
    qs = parse_qs(parsed.query)

    ts = qs.get("dmTs", [""])[0]
    v1st = qs.get("dmV1st", [""])[0]

    return {
        "Host": parsed.netloc,
        "Connection": "keep-alive",
        "sec-ch-ua-platform": "\"Android\"",
        "X-Request-Origin": "player-web-b2b",
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 10; K) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/140.0.0.0 Mobile Safari/537.36"
        ),
        "sec-ch-ua": "\"Chromium\";v=\"140\", \"Not=A?Brand\";v=\"24\", \"Google Chrome\";v=\"140\"",
        "sec-ch-ua-mobile": "?1",
        "Accept": "*/*",
        "Origin": "https://geo.dailymotion.com",
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Storage-Access": "active",
        "Referer": "https://geo.dailymotion.com/",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "id,en-US;q=0.9,en;q=0.8,vi;q=0.7",
        "Cookie": f"ts={ts}; v1st={v1st}; usprivacy=1---; dmvk=68db4d7f75189",
    }


def parse_master_playlist(m3u8_url, proxies):
    """Fetch master playlist .m3u8 dan cari variant kualitas tertinggi."""
    headers = build_m3u8_headers(m3u8_url)
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
                    if h > best_res:
                        best_res = h
                        if i + 1 < len(lines):
                            best_url = lines[i + 1]
                except Exception:
                    pass
    return best_url, best_res


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

        if "auto" in qualities:
            hls_master_url = qualities["auto"][0]["url"]
            print(f"[✓] Dapat master playlist (auto): {hls_master_url}")

            best_variant_url, best_res = parse_master_playlist(hls_master_url, proxies)
            if best_variant_url:
                print(f"[✓] Variant kualitas tertinggi ({best_res}p): {best_variant_url}")
                final_url = best_variant_url
            else:
                print("[!] Gagal cari variant dari master, fallback ke master")
                final_url = hls_master_url
        else:
            numeric_qualities = [int(q) for q in qualities.keys() if q.isdigit()]
            if numeric_qualities:
                best_quality = str(max(numeric_qualities))
                final_url = qualities[best_quality][0]["url"]
                print(f"[✓] Dapat langsung kualitas {best_quality}p dari API: {final_url}")
            else:
                key_some = list(qualities.keys())[0]
                final_url = qualities[key_some][0]["url"]
                print(f"[✓] Fallback ke kualitas {key_some}: {final_url}")

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
