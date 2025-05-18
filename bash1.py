import os
import subprocess
import datetime
from pathlib import Path

REPO_NAME = "RENYAHKU"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"
COOKIES_FILE = os.path.expanduser("~/cookies.txt")
URL_FILE = os.path.expanduser("~/urls.txt")
ROOT_DIR = Path(os.getcwd())
LOG_FILE = ROOT_DIR / "yt-download.log"

def log(msg):
    timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    line = f"{timestamp} {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def clean_log():
    if LOG_FILE.exists():
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        with open(LOG_FILE) as f:
            lines = [line for line in f if line.startswith(f"[{today}") or line.startswith(f"[{yesterday}")]
        with open(LOG_FILE, "w") as f:
            f.writelines(lines)

def get_yt_dlp_output(url, format_code="18"):
    try:
        cmd = [
            "yt-dlp", "--cookies", COOKIES_FILE,
            "--user-agent", USER_AGENT, "-g", "-f", format_code, url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            log(f"[!] yt-dlp gagal dengan kode {result.returncode} untuk {url}")
            return ""
    except Exception as e:
        log(f"[!] yt-dlp error: {e}")
        return ""

def process_urls():
    if not os.path.exists(URL_FILE):
        log(f"[!] File {URL_FILE} tidak ditemukan")
        return

    with open(URL_FILE) as f:
        for line in f:
            if not line.strip() or line.strip().startswith("#"):
                continue
            try:
                name, url = line.strip().split(None, 1)
            except ValueError:
                log(f"[!] Baris tidak valid: {line.strip()}")
                continue

            safe_name = "".join(c for c in name if c.isalnum() or c in "_.-")
            log(f"[*] Memproses: {name}")

            if "playlist?list=" in url:
                cmd = [
                    "yt-dlp", "--cookies", COOKIES_FILE,
                    "--user-agent", USER_AGENT,
                    "-j", "--flat-playlist", url
                ]
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    if result.returncode != 0:
                        log(f"[!] Gagal ambil daftar playlist untuk: {url}")
                        continue
                    for line_pl in result.stdout.strip().splitlines():
                        if '"id":' in line_pl:
                            vid = line_pl.split('"id":')[1].split('"')[1]
                            direct_url = get_yt_dlp_output(f"https://www.youtube.com/watch?v={vid}")
                            if direct_url:
                                filename = ROOT_DIR / f"{safe_name}_{vid}.txt"
                                filename.write_text(direct_url)
                                log(f"[✓] URL MP4 dari playlist disimpan: {filename.name}")
                            else:
                                log(f"[!] Gagal ambil video MP4 dari playlist ({vid})")
                except Exception as e:
                    log(f"[!] Exception saat proses playlist: {e}")

            else:
                direct_url = get_yt_dlp_output(url)
                if direct_url:
                    filename = ROOT_DIR / f"{safe_name}.txt"
                    filename.write_text(direct_url)
                    log(f"[✓] URL MP4 disimpan: {filename.name}")
                else:
                    log(f"[!] Gagal ambil URL MP4 untuk: {url}")

def git_push():
    subprocess.run(["git", "config", "user.name", "GitHub Actions"], check=False)
    subprocess.run(["git", "config", "user.email", "actions@github.com"], check=False)
    subprocess.run(["git", "add", "."], check=False)
    diff_check = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if diff_check.returncode != 0:
        subprocess.run(["git", "commit", "-m", f"Update dari {REPO_NAME}/python - {datetime.datetime.now()}"])
    else:
        log("[i] Tidak ada perubahan untuk commit")

    subprocess.run(["git", "fetch", "origin", "master"], check=False)
    subprocess.run(["git", "merge", "--strategy=ours", "origin/master"], check=False)
    subprocess.run(["git", "push", "origin", "master"], check=False)

if __name__ == "__main__":
    clean_log()
    process_urls()
    git_push()
