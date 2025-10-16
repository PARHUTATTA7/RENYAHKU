#!/usr/bin/env python3
import requests
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import re

# Lokasi file konfigurasi & cache
DAYLIDATA = Path.home() / "daylidata.txt"
PROXY_CACHE_FILE = Path("proxy_ok.txt")
session = requests.Session()


def load_multi_config(path):
    """Baca beberapa blok konfigurasi dari daylidata.txt"""
    try:
        content = Path(path).read_text(encoding="utf-8")
        blocks = re.split(r"#\s*=====+", content)
        configs = []

        for block in blocks:
            block = block.strip()
            if not block:
                continue
            config = {}
            try:
                exec(block, {}, config)
                configs.append(config)
            except Exception as e:
                print(f"[!] Gagal parsing blok: {e}")
        return configs
    except Exception as e:
        print(f"[!] Gagal membaca file konfigurasi: {e}")
        return []


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


def build_m3u8_headers(m3u8_url):
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
        "Accept-Language": "id,en-US;q=0.9,en;q=0.8",
        "Cookie": f"ts={ts}; v1st={v1st}; usprivacy=1---; dmvk=68db4d7f75189",
    }


def parse_master_playlist(m3u8_url, proxies):
    headers = build_m3u8_headers(m3u8_url)
    res = session.get(m3u8_url, headers=headers, proxies=proxies, timeout=10)
    res.raise_for_status()

    lines = res.text.splitlines()
    best_url = None
    best_res = 0

    for i, line in enumerate(lines):
        if line.startswith("#EXT-X-STREAM-INF"):
            match = re.search(r"RESOLUTION=(\d+)x(\d+)", line)
            if match:
                _, h = map(int, match.groups())
                if h > best_res and i + 1 < len(lines):
                    best_res = h
                    best_url = lines[i + 1]
    return best_url, best_res


def try_proxy(proxy, dailymotion_url, meta_url_template, output_file):
    proxies = {"http": proxy, "https": proxy}
    try:
        print(f"[•] Coba proxy: {proxy}")
        video_id = dailymotion_url.split('/video/')[1].split('_')[0]
        meta_url = meta_url_template.format(video_id=video_id)

        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://sevenhub.id/", "Origin": "https://sevenhub.id"}
        res = session.get(meta_url, headers=headers, proxies=proxies, timeout=10)
        res.raise_for_status()

        meta = res.json()
        qualities = meta.get("qualities", {})
        if not qualities:
            print("[!] Tidak ada kualitas video")
            return False

        if "auto" in qualities:
            hls_master_url = qualities["auto"][0]["url"]
            print(f"[✓] Master playlist: {hls_master_url}")
            best_variant_url, best_res = parse_master_playlist(hls_master_url, proxies)
            final_url = best_variant_url or hls_master_url
            print(f"[✓] Final: {final_url}")
        else:
            numeric_qualities = [int(q) for q in qualities.keys() if q.isdigit()]
            if numeric_qualities:
                best_quality = str(max(numeric_qualities))
                final_url = qualities[best_quality][0]["url"]
            else:
                key_some = list(qualities.keys())[0]
                final_url = qualities[key_some][0]["url"]

        Path(output_file).write_text(final_url + "\n")
        print(f"[✓] Simpan ke {output_file}")
        save_working_proxy(proxy)
        return True
    except Exception as e:
        print(f"[×] Proxy gagal {proxy}: {e}")
        return False


def fallback_write(fallback_url, output_file):
    try:
        print(f"[!] Fallback: {fallback_url}")
        res = session.get(fallback_url, timeout=10)
        res.raise_for_status()
        Path(output_file).write_text(res.text)
        print(f"[✓] Fallback disimpan ke {output_file}")
    except Exception as e:
        print(f"[×] Gagal fallback: {e}")


def process_video(cfg):
    DAILYMOTION_URL = cfg.get("DAILYMOTION_URL")
    FALLBACK_URL = cfg.get("FALLBACK_URL")
    url_proxy = cfg.get("url_proxy")
    meta_url = cfg.get("meta_url")
    OUTPUT_FILE = cfg.get("OUTPUT_FILE", "output.txt")

    if not all([DAILYMOTION_URL, FALLBACK_URL, url_proxy, meta_url]):
        print("❌ Konfigurasi tidak lengkap, lewati blok ini.")
        return

    print(f"\n🎬 Proses video: {DAILYMOTION_URL}")
    cached_proxy = load_cached_proxy()
    if cached_proxy and try_proxy(cached_proxy, DAILYMOTION_URL, meta_url, OUTPUT_FILE):
        print("✅ Berhasil dengan proxy cache")
        return

    proxies = get_proxies(url_proxy)
    for proxy in proxies:
        if try_proxy(proxy, DAILYMOTION_URL, meta_url, OUTPUT_FILE):
            print("✅ Berhasil ambil m3u8")
            return

    print("❌ Semua proxy gagal, fallback...")
    fallback_write(FALLBACK_URL, OUTPUT_FILE)


def main():
    configs = load_multi_config(DAYLIDATA)
    if not configs:
        print("❌ Tidak ada blok konfigurasi ditemukan.")
        return

    for cfg in configs:
        process_video(cfg)


if __name__ == "__main__":
    main()
