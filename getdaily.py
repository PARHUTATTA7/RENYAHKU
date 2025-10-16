#!/usr/bin/env python3
import requests
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import re

# Lokasi file konfigurasi
DAYLIDATA = Path.home() / "daylidata.txt"
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


def parse_master_playlist(m3u8_url):
    """Cari variant kualitas tertinggi dari master.m3u8"""
    headers = build_m3u8_headers(m3u8_url)
    res = session.get(m3u8_url, headers=headers, timeout=10)
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


def fetch_dailymotion_url(dailymotion_url, meta_url_template, output_file, fallback_url):
    try:
        video_id = dailymotion_url.split('/video/')[1].split('_')[0]
        meta_url = meta_url_template.format(video_id=video_id)

        print(f"🎬 Ambil metadata untuk ID: {video_id}")
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://sevenhub.id/",
            "Origin": "https://sevenhub.id",
        }

        res = session.get(meta_url, headers=headers, timeout=10)
        res.raise_for_status()
        meta = res.json()
        qualities = meta.get("qualities", {})

        if not qualities:
            print("[!] Tidak ada kualitas video di metadata")
            return False

        if "auto" in qualities:
            hls_master_url = qualities["auto"][0]["url"]
            print(f"[✓] Master playlist: {hls_master_url}")
            best_variant_url, best_res = parse_master_playlist(hls_master_url)
            final_url = best_variant_url or hls_master_url
            print(f"[✓] Final URL ({best_res}p): {final_url}")
        else:
            numeric_qualities = [int(q) for q in qualities.keys() if q.isdigit()]
            if numeric_qualities:
                best_quality = str(max(numeric_qualities))
                final_url = qualities[best_quality][0]["url"]
            else:
                key_some = list(qualities.keys())[0]
                final_url = qualities[key_some][0]["url"]

        Path(output_file).write_text(final_url + "\n", encoding="utf-8")
        print(f"[✅] Simpan hasil ke {output_file}")
        return True

    except Exception as e:
        print(f"[×] Gagal ambil data utama: {e}")
        if fallback_url:
            try:
                print(f"[!] Gunakan fallback: {fallback_url}")
                r = session.get(fallback_url, timeout=10)
                r.raise_for_status()
                Path(output_file).write_text(r.text, encoding="utf-8")
                print(f"[✅] Fallback tersimpan ke {output_file}")
                return True
            except Exception as ef:
                print(f"[×] Gagal fallback juga: {ef}")
        return False


def process_video(cfg):
    DAILYMOTION_URL = cfg.get("DAILYMOTION_URL")
    FALLBACK_URL = cfg.get("FALLBACK_URL")
    meta_url = cfg.get("meta_url")
    OUTPUT_FILE = cfg.get("OUTPUT_FILE")

    if not all([DAILYMOTION_URL, FALLBACK_URL, meta_url]):
        print("❌ Konfigurasi tidak lengkap. Lewati blok ini.")
        return

    if not OUTPUT_FILE:
        video_id = DAILYMOTION_URL.split('/video/')[1].split('_')[0]
        OUTPUT_FILE = f"{video_id}.txt"

    print(f"\n▶️ Proses: {DAILYMOTION_URL}")
    success = fetch_dailymotion_url(DAILYMOTION_URL, meta_url, OUTPUT_FILE, FALLBACK_URL)
    if not success:
        print(f"[×] Gagal ambil M3U8 untuk {DAILYMOTION_URL}")
    else:
        print(f"[✓] Selesai untuk {OUTPUT_FILE}")


def main():
    configs = load_multi_config(DAYLIDATA)
    if not configs:
        print("❌ Tidak ada blok konfigurasi ditemukan.")
        return

    for cfg in configs:
        process_video(cfg)


if __name__ == "__main__":
    main()
