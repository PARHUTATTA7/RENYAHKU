#!/usr/bin/env python3

import subprocess
import datetime
from pathlib import Path
import json
import argparse
import re
import sys

REPO_NAME = "RENYAHKU"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"
COOKIES_FILE = str(Path.home() / "cookies.txt")
URL_FILE = Path.home() / "urls_live.txt"
WORKDIR = Path(".")

def run_cmd(cmd):
    try:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=True, encoding="utf-8", errors="ignore"
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"[DEBUG] Command failed: {' '.join(cmd)}")
        print(f"[DEBUG] Error: {e.stderr}")
        return ""

def fetch_html(url):
    return run_cmd([
        "curl", "-A", USER_AGENT,
        "-L", "-s", "--cookie", COOKIES_FILE,
        "--retry", "3", "--max-time", "30",
        url
    ])

def get_yt_dlp_output(url, format_code="best[ext=m3u8]", from_start=True):
    if not url:
        return ""
    
    cmd = [
        "yt-dlp", "--no-warnings", 
        "--cookies", COOKIES_FILE,
        "--user-agent", USER_AGENT,
        "-g", "-f", format_code,
        "--no-check-certificates"
    ]
    
    if from_start:
        cmd.append("--live-from-start")
    
    cmd.append(url)
    
    output = run_cmd(cmd)
    lines = output.splitlines()
    
    # Debug output
    if output:
        print(f"[DEBUG] yt-dlp output ({format_code}): {output[:100]}...")
    
    return lines[-1] if lines else ""

def get_video_id(url):
    print(f"[DEBUG] Getting video ID for: {url}")
    
    # Cek jika sudah berupa URL dengan v= parameter
    if "youtube.com/watch?v=" in url:
        match = re.search(r"v=([A-Za-z0-9_-]{11})", url)
        if match:
            vid = match.group(1)
            print(f"[DEBUG] Found video ID from URL: {vid}")
            return vid
    
    # 0) Fetch HTML dan cari canonical URL
    html = fetch_html(url)
    if html:
        # Pattern untuk canonical URL
        patterns = [
            r'<link rel="canonical" href="https://www\.youtube\.com/watch\?v=([A-Za-z0-9_-]{11})"',
            r'"videoId":"([A-Za-z0-9_-]{11})"',
            r'watch\?v=([A-Za-z0-9_-]{11})',
        ]
        
        for pattern in patterns:
            m = re.search(pattern, html)
            if m:
                vid = m.group(1)
                print(f"[DEBUG] Found video ID from HTML: {vid}")
                return vid
    
    # 1) Coba dengan yt-dlp get-id
    vid = run_cmd([
        "yt-dlp", "--no-warnings",
        "--cookies", COOKIES_FILE,
        "--user-agent", USER_AGENT,
        "--get-id", "--no-check-certificates",
        url
    ]).strip()
    
    if vid and len(vid) == 11:
        print(f"[DEBUG] Got video ID from yt-dlp: {vid}")
        return vid
    
    # 2) Untuk channel live streams (/@username/live)
    m2 = re.search(r"youtube\.com/@([^/]+)/live", url)
    if not m2:
        m2 = re.search(r"youtube\.com/c/([^/]+)/live", url)
    
    if m2:
        username = m2.group(1)
        print(f"[DEBUG] Looking for live stream for: @{username}")
        
        # Coba beberapa format pencarian
        search_queries = [
            f"ytsearch1:{username} live",
            f"ytsearch1:https://www.youtube.com/@{username}/live",
            f"ytsearch1:https://www.youtube.com/c/{username}/live"
        ]
        
        for search_query in search_queries:
            data = run_cmd([
                "yt-dlp", "--no-warnings",
                "--cookies", COOKIES_FILE,
                "--user-agent", USER_AGENT,
                "--dump-single-json", "--no-check-certificates",
                search_query
            ])
            
            if data:
                try:
                    info = json.loads(data)
                    entries = info.get("entries", [])
                    if not entries and isinstance(info, dict) and "id" in info:
                        # Handle single entry
                        entries = [info]
                    
                    for entry in entries:
                        if entry and entry.get("live_status") in ("is_live", "post_live", "was_live"):
                            video_id = entry.get("id", "")
                            if video_id:
                                print(f"[DEBUG] Found live video ID: {video_id}")
                                return video_id
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"[DEBUG] JSON parse error: {e}")
                    continue
    
    print(f"[DEBUG] Could not find video ID")
    return ""

def safe_filename(name):
    # Hapus karakter tidak aman untuk nama file
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = re.sub(r'\s+', '_', name)
    return name.strip('_.')

def main():
    parser = argparse.ArgumentParser(description="Download YouTube live stream URLs")
    parser.add_argument("--no-from-start", action="store_true", 
                       help="Don't use --live-from-start flag")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug output")
    args = parser.parse_args()

    use_from_start = not args.no_from_start

    if not URL_FILE.exists():
        print(f"[!] File {URL_FILE} tidak ditemukan")
        sys.exit(1)

    # Cek apakah yt-dlp tersedia
    yt_dlp_check = subprocess.run(["yt-dlp", "--version"], 
                                 capture_output=True, text=True)
    if yt_dlp_check.returncode != 0:
        print("[!] yt-dlp tidak ditemukan atau tidak dapat dijalankan")
        sys.exit(1)

    with URL_FILE.open("r", encoding="utf-8") as f:
        lines = f.readlines()
    
    print(f"[*] Found {len(lines)} entries to process")
    
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
            
        try:
            # Split dengan maksimal 1 split untuk menangani URL dengan spasi
            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                print(f"[!] Format salah pada baris {line_num}: {line}")
                continue
                
            name, url = parts
            safe_name = safe_filename(name)
            print(f"\n[{line_num}] Memproses: {name} -> {url}")
            
            # Bersihkan URL dari karakter yang tidak diinginkan
            url = url.strip()
            
            # Coba beberapa format URL jika perlu
            video_id = get_video_id(url)
            
            if not video_id:
                print(f"[!] Tidak bisa mendapatkan video ID dari: {url}")
                continue
                
            resolved_url = f"https://www.youtube.com/watch?v={video_id}"
            print(f"[*] Resolved URL: {resolved_url}")
            
            # Coba beberapa format untuk mendapatkan m3u8
            formats_to_try = [
                "best[ext=m3u8]",
                "best[ext=mp4]/best[ext=webm]/best",
                "best"
            ]
            
            m3u8_url = ""
            for fmt in formats_to_try:
                print(f"[*] Mencoba format: {fmt}")
                m3u8_url = get_yt_dlp_output(resolved_url, fmt, from_start=use_from_start)
                if m3u8_url and m3u8_url.startswith(("http://", "https://")):
                    print(f"[✓] Berhasil mendapatkan URL dengan format {fmt}")
                    break
                else:
                    print(f"[!] Gagal dengan format {fmt}")
            
            if not m3u8_url:
                print(f"[!] Gagal ambil URL streaming untuk: {resolved_url}")
                continue
                
            out_path = WORKDIR / f"{safe_name}.m3u8.txt"
            out_path.write_text(m3u8_url, encoding="utf-8")
            print(f"[✓] URL streaming disimpan: {out_path.name}")
            print(f"[✓] URL: {m3u8_url[:80]}...")
            
        except Exception as e:
            print(f"[!] Error processing line {line_num}: {e}")
            continue

    # Git operations
    print("\n[*] Melakukan operasi git...")
    try:
        subprocess.run(["git", "config", "user.email", "actions@github.com"], check=False)
        subprocess.run(["git", "config", "user.name", "GitHub Actions"], check=False)
        subprocess.run(["git", "add", "."], check=False)
        
        # Check if there are changes
        result = subprocess.run(["git", "status", "--porcelain"], 
                              capture_output=True, text=True, check=False)
        
        if result.stdout.strip():
            commit_msg = f"Update dari {REPO_NAME} - {datetime.datetime.now():%Y-%m-%d %H:%M:%S}"
            subprocess.run(["git", "commit", "-m", commit_msg], check=False)
            print(f"[✓] Committed changes: {commit_msg}")
            
            # Pull before push to avoid conflicts
            subprocess.run(["git", "pull", "--rebase", "origin", "master"], check=False)
            subprocess.run(["git", "push", "origin", "master"], check=False)
            print("[✓] Pushed to remote")
        else:
            print("[*] Tidak ada perubahan, skip commit")
            
    except Exception as e:
        print(f"[!] Git error: {e}")

if __name__ == "__main__":
    main()
