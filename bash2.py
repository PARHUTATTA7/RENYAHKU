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
# Ambil HLS dari sebuah PAGE (TAB)
# ============================================================
async def get_hls_from_page(page, url):
    try:
        await page.goto(url, wait_until="networkidle", timeout=60000)
    except PlaywrightTimeout:
        print("❌ Timeout YouTube:", url)
        return None
    except:
        print("❌ Gagal buka halaman:", url)
        return None

    html = await page.content()

    pattern_main = r"ytInitialPlayerResponse\s*=\s*({.*?})\s*;"
    match = re.search(pattern_main, html, re.S)

    if not match:
        pattern_alt = r'"_yt_player_response":\s*({.*?})\s*,\s*"responseContext"'
        match = re.search(pattern_alt, html, re.S)

    if not match:
        print("❌ Tidak menemukan ytInitialPlayerResponse!")
        return None

    try:
        data = json.loads(match.group(1))
    except:
        print("❌ JSON ytInitialPlayerResponse corrupt!")
        return None

    streaming = data.get("streamingData", {})
    hls = streaming.get("hlsManifestUrl")

    if not hls:
        print("❌ hlsManifestUrl tidak ditemukan!")
        return None

    return hls


def safe_filename(name):
    return "".join(c for c in name if c.isalnum() or c in "_.-")


# ============================================================
# Versi PARALLEL — 1 browser → banyak URL
# ============================================================
async def process_all_parallel():
    if not URL_FILE.exists():
        print(f"[!] File {URL_FILE} tidak ditemukan")
        return

    tasks = []
    items = []

    # baca input URL dulu
    with URL_FILE.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip() or line.startswith("#"):
                continue

            try:
                name, url = line.strip().split(maxsplit=1)
                items.append((name, url))
            except:
                continue

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent=USER_AGENT)

        for name, url in items:
            page = await ctx.new_page()
            safe_name = safe_filename(name)
            print(f"\n[*] Paralel: {name}")

            task = asyncio.create_task(
                worker_task(page, safe_name, url)
            )
            tasks.append(task)

        await asyncio.gather(*tasks)

        await browser.close()


# ============================================================
# Worker untuk setiap tab
# ============================================================
async def worker_task(page, safe_name, url):
    print(f"[•] Ambil HLS → {safe_name}")

    m3u8_url = await get_hls_from_page(page, url)

    if not m3u8_url:
        print(f"[!] Gagal ambil HLS untuk {safe_name}")
        return

    out_path = WORKDIR / f"{safe_name}.m3u8.txt"
    out_path.write_text(m3u8_url, encoding="utf-8")

    print(f"[✓] Selesai → {out_path.name}")


# ============================================================
# GIT WORKFLOW
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
    asyncio.run(process_all_parallel())
    do_git()


if __name__ == "__main__":
    main()
