#!/usr/bin/env python3
import subprocess
import requests
import re
from pathlib import Path
from datetime import datetime

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"
)

URL_FILE = Path.home() / "TESTYT_live.txt"
WORKDIR = Path(".")

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode()
    except:
        return ""

# =======================================================
# 1. Video ID LANGSUNG DARI URL
# =======================================================
def get_video_id(url: str):
    print(f"    [DBG] URL: {url}")

    m = re.search(r"v=([A-Za-z0-9_-]{11})", url)
    if m:
        vid = m.group(1)
        print(f"    [DBG] VIDEO ID (direct): {vid}")
        return vid

    print("    [DBG] FAILED — URL tidak mengandung watch?v=")
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

        # LANGSUNG extract ID
        vid = get_video_id(url)
        if not vid:
            print(f"[!] Tidak bisa extract video ID dari URL: {url}")
            continue

        # Ambil master playlist
        print(f"    → Video ID: {vid}")
        m3u8 = get_master_m3u8(vid)
        if not m3u8:
            print("[!] Gagal ambil master HLS via Invidious!")
            continue

        # Simpan file
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
