import subprocess
import datetime
import os
import random
import urllib.request
from pathlib import Path

REPO_NAME = "RENYAHKU"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"
COOKIES_FILE = str(Path.home() / "cookies.txt")
URL_FILE = Path.home() / "urls_live.txt"
PROXY_LIST_URL_FILE = Path.home() / "proxylisturl.txt"
LOG_FILE = Path("yt-m3u8.log")
WORKDIR = Path(".")

def log(msg):
    timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    line = f"{timestamp} {msg}"
    print(line)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

def clean_log():
    if not LOG_FILE.exists():
        return
    today = datetime.date.today().strftime("%Y-%m-%d")
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    with LOG_FILE.open("r", encoding="utf-8") as f:
        lines = [line for line in f if line.startswith(f"[{today}") or line.startswith(f"[{yesterday}")]
    LOG_FILE.write_text("".join(lines), encoding="utf-8")

def get_random_proxy():
    if not PROXY_LIST_URL_FILE.exists():
        log(f"[!] File proxy list URL tidak ditemukan: {PROXY_LIST_URL_FILE}")
        return None
    try:
        url = PROXY_LIST_URL_FILE.read_text().strip()
        with urllib.request.urlopen(url) as response:
            lines = response.read().decode().splitlines()
            proxies = [line.strip() for line in lines if line.strip() and ":" in line]
            if not proxies:
                return None
            return random.choice(proxies)
    except Exception as e:
        log(f"[!] Gagal mengambil daftar proxy: {e}")
        return None

def get_yt_dlp_output(url, format_code="best[ext=m3u8]", proxy=None):
    cmd = [
        "yt-dlp", "--cookies", COOKIES_FILE, "--user-agent", USER_AGENT,
        "-g", "-f", format_code, url
    ]
    if proxy:
        cmd.extend(["--proxy", f"http://{proxy}"])
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=True,
            encoding="utf-8"
        )
        lines = result.stdout.strip().splitlines()
        return lines[-1] if lines else ""
    except subprocess.CalledProcessError:
        return ""

def get_video_id(url, proxy=None):
    cmd = [
        "yt-dlp", "--cookies", COOKIES_FILE, "--get-id", url
    ]
    if proxy:
        cmd.extend(["--proxy", f"http://{proxy}"])
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

def safe_filename(name):
    return "".join(c for c in name if c.isalnum() or c in "_.-")

def main():
    clean_log()

    if not URL_FILE.exists():
        log(f"[!] File {URL_FILE} tidak ditemukan")
        return

    proxy = get_random_proxy()
    if proxy:
        log(f"[✓] Menggunakan proxy: {proxy}")
    else:
        log("[i] Tidak menggunakan proxy")

    with URL_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip() or line.strip().startswith("#"):
                continue
            try:
                name, url = line.strip().split(maxsplit=1)
            except ValueError:
                continue
            safe_name = safe_filename(name)
            log(f"[*] Memproses: {name}")

            video_id = get_video_id(url, proxy)
            if not video_id:
                log(f"[!] Tidak bisa resolve video ID dari: {url}")
                continue

            resolved_url = f"https://www.youtube.com/watch?v={video_id}"
            m3u8_url = get_yt_dlp_output(resolved_url, "best[ext=m3u8]", proxy)

            if not m3u8_url:
                log(f"[!] Gagal ambil URL .m3u8, coba fallback format best")
                m3u8_url = get_yt_dlp_output(resolved_url, "best", proxy)

            if not m3u8_url:
                log(f"[!] Gagal ambil URL streaming untuk: {resolved_url}")
                continue

            out_path = WORKDIR / f"{safe_name}.m3u8.txt"
            out_path.write_text(m3u8_url, encoding="utf-8")
            log(f"[✓] URL streaming disimpan: {out_path.name}")

    subprocess.run(["git", "config", "user.email", "actions@github.com"])
    subprocess.run(["git", "config", "user.name", "GitHub Actions"])
    subprocess.run(["git", "add", "."], check=False)

    diff_check = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if diff_check.returncode != 0:
        commit_msg = f"Update dari {REPO_NAME}/bash2.py - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        subprocess.run(["git", "commit", "-m", commit_msg])
    else:
        log("[i] Tidak ada perubahan untuk commit")

    subprocess.run(["git", "fetch", "origin", "master"])
    subprocess.run(["git", "merge", "--strategy=ours", "origin/master"], check=False)
    subprocess.run(["git", "push", "origin", "master"], check=False)

if __name__ == "__main__":
    main()
