#!/usr/bin/env python3

import subprocess
import datetime
from pathlib import Path
import json
import argparse
import re

REPO_NAME = "RENYAHKU"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"
COOKIES_FILE = str(Path.home() / "cookies.txt")
URL_FILE = Path.home() / "urls_live.txt"
WORKDIR = Path(".")

def run_cmd(cmd):
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=True,
            encoding="utf-8"
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return ""

def fetch_html(url):
    return run_cmd([
        "curl", "-A", USER_AGENT,
        "-L", "-s", "--cookie", COOKIES_FILE,
        url
    ])

# 🔥 FIX PENTING → AMBIL MASTER .m3u8, BUKAN FORMAT PER-KUALITAS
def get_master_m3u8(url):
    if not url:
        return ""

    cmd = [
        "yt-dlp",
        "--no-warnings",
        "--cookies", COOKIES_FILE,
        "--user-agent", USER_AGENT,
        "--print", "%(manifest_url)s",
        url
    ]

    output = run_cmd(cmd)
    # Validasi benar file HLS master
    if output.startswith("http") and "m3u8" in output:
        return output

    return ""

def get_video_id(url):
    html = fetch_html(url)
    if html:
        m = re.search(
            r'<link rel="canonical" href="https://www\.youtube\.com/watch\?v=([A-Za-z0-9_-]{11})"',
            html
        )
        if m:
            return m.group(1)

    vid = run_cmd([
        "yt-dlp", "--no-warnings",
        "--cookies", COOKIES_FILE,
        "--user-agent", USER_AGENT,
        "--get-id", url
    ]).strip()

    if vid:
        return vid

    m2 = re.search(r"youtube\.com/@([^/]+)/?live?", url)
    if m2:
        username = m2.group(1)
        search_query = f"ytsearch5:{username} live"

        data = run_cmd([
            "yt-dlp", "--no-warnings",
            "--cookies", COOKIES_FILE,
            "--user-agent", USER_AGENT,
            "--dump-single-json", search_query
        ])

        try:
            info = json.loads(data)
            for e in info.get("entries", []):
                if e and e.get("live_status") in ("is_live", "live"):
                    return e.get("id", "")
        except:
            pass

    return ""

def safe_filename(name):
    return "".join(c for c in name if c.isalnum() or c in "_.-")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-from-start", action="store_true")
    args = parser.parse_args()

    if not URL_FILE.exists():
        print(f"[!] File {URL_FILE} tidak ditemukan")
        return

    with URL_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip() or line.strip().startswith("#"):
                continue
            try:
                name, url = line.strip().split(maxsplit=1)
            except ValueError:
                continue

            safe_name = safe_filename(name)
            print(f"[*] Memproses: {name}")

            video_id = get_video_id(url)
            if not video_id:
                print(f"[!] Tidak bisa resolve video ID dari: {url}")
                continue

            resolved_url = f"https://www.youtube.com/watch?v={video_id}"

            # 🔥 ambil master HLS
            m3u8_url = get_master_m3u8(resolved_url)

            if not m3u8_url:
                print(f"[!] Gagal ambil master .m3u8 untuk: {resolved_url}")
                continue

            out_path = WORKDIR / f"{safe_name}.m3u8.txt"
            out_path.write_text(m3u8_url, encoding="utf-8")
            print(f"[✓] Master HLS disimpan: {out_path.name}")

    # Git ops
    subprocess.run(["git", "config", "user.email", "actions@github.com"])
    subprocess.run(["git", "config", "user.name", "GitHub Actions"])
    subprocess.run(["git", "add", "."], check=False)

    diff_check = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if diff_check.returncode != 0:
        commit_msg = f"Update dari {REPO_NAME}/bash2.py - {datetime.datetime.now():%Y-%m-%d %H:%M:%S}"
        subprocess.run(["git", "commit", "-m", commit_msg])

    subprocess.run(["git", "fetch", "origin", "master"])
    subprocess.run(["git", "merge", "--strategy=ours", "origin/master"], check=False)
    subprocess.run(["git", "push", "origin", "master"], check=False)

if __name__ == "__main__":
    main()
