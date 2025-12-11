#!/usr/bin/env python3
import subprocess
import requests
import re
import json
from pathlib import Path
from datetime import datetime

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"
)

URL_FILE = Path.home() / "urls_live.txt"
WORKDIR = Path(".")

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode()
    except:
        return ""

def fetch_html(url: str):
    try:
        return requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10).text
    except:
        return ""

# =======================================================
# 1. Resolve Video ID Langsung
# =======================================================
def get_video_id(url: str):
    print(f"    [DBG] URL: {url}")

    # ---------- 1. yt-dlp JSON ----------
    json_text = run_cmd(["yt-dlp", "--no-warnings", "--dump-single-json", url])
    print(f"    [DBG] Sumber yt-dlp JSON loaded: {'YES' if json_text else 'NO'}")

    print("    [DBG] Semua kandidat ID dari yt-dlp:")
    cand = re.findall(r'"id":\s*"([A-Za-z0-9_-]{11})"', json_text)
    for i in cand:
        print(f"        → {i}")

    for vid in cand:
        if not vid.startswith("UC"):
            print(f"    [DBG] PICKED (yt-dlp): {vid}")
            return vid

    # ---------- 2. LOAD HTML ----------
    html = fetch_html(url)
    print(f"    [DBG] HTML Loaded: {'YES' if html else 'NO'}")

    # 2a. Canonical (FIXED)
    canonical = re.findall(
        r'rel=["\']canonical["\'][^>]*href=["\']https://www\.youtube\.com/watch\?v=([A-Za-z0-9_-]{11})',
        html
    )
    print(f"    [DBG] Canonical ID: {canonical[0] if canonical else ''}")

    if canonical:
        print(f"    [DBG] PICKED (canonical): {canonical[0]}")
        return canonical[0]

    # 2b. currentVideoEndpoint
    cur = re.findall(
        r'"currentVideoEndpoint":\s*{"videoId":"([A-Za-z0-9_-]{11})"',
        html
    )
    print(f"    [DBG] currentVideoEndpoint.videoId: {cur[0] if cur else ''}")

    if cur:
        print(f"    [DBG] PICKED (currentVideoEndpoint): {cur[0]}")
        return cur[0]

    # ---------- 3. Fallback Search (FIXED) ----------
    match = re.search(r'youtube\.com/@([^/]+)', url)
    if match:
        username = match.group(1)
        print(f"    [DBG] Fallback search username: {username}")

        json2 = run_cmd([
            "yt-dlp", "--no-warnings",
            "--dump-single-json",
            "--match-filter", "is_live",
            f"ytsearchdate10:{username}"
        ])

        print("    [DBG] Semua kandidat ID dari ytsearch:")
        cand2 = re.findall(r'"id":\s*"([A-Za-z0-9_-]{11})"', json2)
        for i in cand2:
            print(f"        → {i}")

        for vid in cand2:
            if not vid.startswith("UC"):
                print(f"    [DBG] PICKED (ytsearch-live): {vid}")
                return vid

    print("    [DBG] FAILED — No valid ID found")
    return ""

# =======================================================
# 2. Ambil Master M3U8 via Invidious
# =======================================================
def get_master_m3u8(video_id: str):
    embed = f"https://invidious.nerdvpn.de/embed/{video_id}"
    url = run_cmd([
        "yt-dlp", "-g",
        "--no-warnings",
        "--user-agent", USER_AGENT,
        embed
    ])
    return url.strip()

# =======================================================
# MAIN
# =======================================================
def main():
    if not URL_FILE.exists():
        print(f"[!] File {URL_FILE} tidak ditemukan!")
        return

    for line in URL_FILE.read_text().splitlines():
        if not line or line.startswith("#"): 
            continue

        parts = line.split(maxsplit=1)
        name = parts[0]
        url = parts[1]
        safe = re.sub(r'[^A-Za-z0-9_.-]', '_', name)

        print(f"[*] Memproses: {name}")

        vid = get_video_id(url)
        if not vid:
            print(f"[!] Tidak bisa resolve video ID: {url}")
            continue

        print(f"    → Video ID: {vid}")

        m3u8 = get_master_m3u8(vid)
        if not m3u8:
            print("[!] Gagal ambil master HLS via Invidious!")
            continue

        out = WORKDIR / f"{safe}.m3u8.txt"
        out.write_text(m3u8)
        print(f"[✓] Disimpan: {out}")

    # Git Ops
    subprocess.call(["git", "config", "user.email", "actions@github.com"])
    subprocess.call(["git", "config", "user.name", "GitHub Actions"])
    subprocess.call(["git", "add", "."])

    try:
        if subprocess.call(["git", "diff", "--cached", "--quiet"]) != 0:
            subprocess.call([
                "git", "commit", "-m",
                f"Update dari RENYAHKU/python - {datetime.now():%Y-%m-%d %H:%M:%S}"
            ])
    except:
        pass

    subprocess.call(["git", "fetch", "origin", "master"])
    subprocess.call(["git", "merge", "--strategy=ours", "origin/master"])
    subprocess.call(["git", "push", "origin", "master"])

if __name__ == "__main__":
    main()
