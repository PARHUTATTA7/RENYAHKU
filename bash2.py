#!/usr/bin/env python3 

import subprocess
import datetime
from pathlib import Path
import json
import argparse
import re
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

REPO_NAME = "RENYAHKU"
URL_FILE = Path.home() / "urls_live.txt"
WORKDIR = Path(".")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "Chrome/120 Safari/537.36"
)

# ============================================================
# PLAYWRIGHT: Ambil HANYA hlsManifestUrl
# ============================================================
async def get_hls_from_youtube(url):
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent=USER_AGENT)
        page = await ctx.new_page()

        try:
            await page.goto(url, wait_until="networkidle", timeout=60000)
        except PlaywrightTimeout:
            print("❌ Timeout saat membuka halaman YouTube")
            return None
        except:
            print("❌ Gagal membuka halaman YouTube")
            return None

        html = await page.content()

        # ============================================================
        # 1️⃣ Regex utama: ytInitialPlayerResponse =
        # ============================================================
        pattern_main = r"ytInitialPlayerResponse\s*=\s*({.*?})\s*;"
        match = re.search(pattern_main, html, re.S)

        # ============================================================
        # 2️⃣ Jika gagal, pakai alternatif _yt_player_response
        # ============================================================
        if not match:
            pattern_alt = r'"_yt_player_response":\s*({.*?})\s*,\s*"responseContext"'
            match = re.search(pattern_alt, html, re.S)

        if not match:
            print("❌ Tidak menemukan ytInitialPlayerResponse di halaman!")
            return None

        # ============================================================
        # Parsing JSON
        # ============================================================
        try:
            data = json.loads(match.group(1))
        except Exception as e:
            print("❌ JSON ytInitialPlayerResponse tidak valid:", e)
            return None

        streaming = data.get("streamingData", {})

        # ============================================================
        # 🔥 Fokus hanya ambil HLS
        # ============================================================
        hls = streaming.get("hlsManifestUrl")

        if not hls:
            print("❌ hlsManifestUrl tidak ditemukan!")
            return None

        return hls


# ============================================================
# HELPER
# ============================================================
def safe_filename(name):
    return "".join(c for c in name if c.isalnum() or c in "_.-")


# ============================================================
# PROCESSOR UTAMA
# ============================================================
async def process_all(use_from_start=True):
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
            print(f"\n[*] Memproses: {name}")

            print("[•] Mengambil HLS dari ytInitialPlayerResponse...")

            m3u8_url = await get_hls_from_youtube(url)

            if not m3u8_url:
                print("[!] Gagal mendapatkan HLS!")
                continue

            out_path = WORKDIR / f"{safe_name}.m3u8.txt"
            out_path.write_text(m3u8_url, encoding="utf-8")

            print(f"[✓] URL HLS disimpan: {out_path.name}")


# ============================================================
# GIT WORKFLOW — tetap sama
# ============================================================
def do_git():
    subprocess.run(["git", "config", "user.email", "actions@github.com"])
    subprocess.run(["git", "config", "user.name", "GitHub Actions"])
    subprocess.run(["git", "add", "."], check=False)

    diff_check = subprocess.run(["git", "diff", "--cached", "--quiet"])
    if diff_check.returncode != 0:
        msg = f"Update dari {REPO_NAME}/bash2.py - {datetime.datetime.now():%Y-%m-%d %H:%M:%S}"
        subprocess.run(["git", "commit", "-m", msg])

    subprocess.run(["git", "fetch", "origin", "master"])
    subprocess.run(["git", "merge", "--strategy=ours", "origin/master"], check=False)
    subprocess.run(["git", "push", "origin", "master"], check=False)


# ============================================================
# ENTRY POINT
# ============================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-from-start", action="store_true")
    args = parser.parse_args()

    asyncio.run(process_all(use_from_start=not args.no_from_start))
    do_git()


if __name__ == "__main__":
    main()
