#!/usr/bin/env python3

import subprocess
import datetime
from pathlib import Path
import json

REPO_NAME = "RENYAHKU"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"
COOKIES_FILE = str(Path.home() / "cookies.txt")
URL_FILE = Path.home() / "urls_live.txt"
WORKDIR = Path(".")

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=True, encoding="utf-8")
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return ""

def get_yt_dlp_output(url, format_code="best[ext=m3u8]"):
    if not url:
        return ""
    output = run_cmd([
        "yt-dlp", "--no-warnings", "--cookies", COOKIES_FILE,
        "--user-agent", USER_AGENT, "-g", "-f", format_code, url
    ])
    lines = output.splitlines()
    return lines[-1] if lines else ""

def get_video_id(url):
    # Coba resolve ID langsung
    vid = run_cmd([
        "yt-dlp", "--no-warnings", "--cookies", COOKIES_FILE,
        "--user-agent", USER_AGENT, "--get-id", url
    ])
    if not vid and "/live" in url:
        # Fallback: paksa ambil ID dari JSON
        data = run_cmd([
            "yt-dlp", "--no-warnings", "--cookies", COOKIES_FILE,
            "--user-agent", USER_AGENT, "--dump-json", "--no-playlist", url
        ])
        try:
            info = json.loads(data)
            vid = info.get("id", "")
            if not info.get("is_live", False):
                print("[i] Channel ditemukan, tapi sedang tidak live.")
        except json.JSONDecodeError:
            vid = ""
    return vid

def safe_filename(name):
    return "".join(c for c in name if c.isalnum() or c in "_.-")

def main():
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
            m3u8_url = get_yt_dlp_output(resolved_url, "best[ext=m3u8]")

            if not m3u8_url:
                print(f"[!] Gagal ambil URL .m3u8, coba fallback format best")
                m3u8_url = get_yt_dlp_output(resolved_url, "best")

            if not m3u8_url:
                print(f"[!] Gagal ambil URL streaming untuk: {resolved_url}")
                continue

            out_path = WORKDIR / f"{safe_name}.m3u8.txt"
            out_path.write_text(m3u8_url, encoding="utf-8")
            print(f"[✓] URL streaming disimpan: {out_path.name}")

    # Git stage, commit, push
    subprocess.run(["git", "config", "user.email", "actions@github.com"])
    subprocess.run(["git", "config", "user.name", "GitHub Actions"])
    subprocess.run(["git", "add", "."], check=False)

    diff_check = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if diff_check.returncode != 0:
        commit_msg = f"Update dari {REPO_NAME}/bash2.py - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", commit_msg])
    else:
        print("[i] Tidak ada perubahan untuk commit")

    subprocess.run(["git", "fetch", "origin", "master"])
    subprocess.run(["git", "merge", "--strategy=ours", "origin/master"], check=False)
    subprocess.run(["git", "push", "origin", "master"], check=False)

if __name__ == "__main__":
    main()
