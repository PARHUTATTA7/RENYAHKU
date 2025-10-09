import requests
import re
import json
from html import unescape
from pathlib import Path
import urllib3
from urllib.parse import urljoin, urlparse

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Lokasi file input
URL_FILE = Path.home() / "page_url.txt"

with open(URL_FILE, encoding="utf-8") as f:
    page_url = f.read().strip()

# 🧩 Buat base domain (untuk Referer & Origin otomatis)
parsed = urlparse(page_url)
base_domain = f"{parsed.scheme}://{parsed.netloc}"

# 🧠 Header dinamis — tanpa hardcode referer/origin
base_headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": base_domain + "/",   # otomatis sesuai domain
    "Origin": base_domain,
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
}

def fetch_html(url, referer=None):
    """Ambil HTML dari URL dengan headers dinamis"""
    headers = base_headers.copy()
    if referer:
        headers["Referer"] = referer
        parsed_ref = urlparse(referer)
        headers["Origin"] = f"{parsed_ref.scheme}://{parsed_ref.netloc}"
    try:
        resp = requests.get(url, headers=headers, verify=False, timeout=20)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"❌ Request error: {e}")
        return ""

def extract_jwp_sources(html):
    """Cari blok jwpSources"""
    match = re.search(r'jwpSources\s*=\s*(\[[\s\S]*?\])\s*,\s*\n\s*drmToken', html)
    if not match:
        return None
    raw_json = match.group(1)
    raw_json = raw_json.encode("utf-8").decode("unicode_escape")
    raw_json = raw_json.replace("\\/", "/")
    raw_json = unescape(raw_json)
    try:
        return json.loads(raw_json)
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        Path("raw_jwpSources.txt").write_text(raw_json, encoding="utf-8")
        print("🔍 Saved raw JSON to raw_jwpSources.txt for debugging")
        return None

def extract_iframe_src(html, base_url):
    """Cari URL iframe di dalam HTML"""
    iframe = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html)
    if iframe:
        return urljoin(base_url, iframe.group(1))
    return None


# ========================
# 1️⃣ Ambil halaman utama
# ========================
html = fetch_html(page_url)
if not html:
    exit()

sources = extract_jwp_sources(html)

# ========================
# 2️⃣ Jika tidak ada, coba iframe
# ========================
if not sources:
    iframe_url = extract_iframe_src(html, page_url)
    if iframe_url:
        print(f"🔗 Found iframe: {iframe_url}")
        iframe_html = fetch_html(iframe_url, referer=page_url)
        sources = extract_jwp_sources(iframe_html)
        if not sources:
            print("❌ jwpSources not found in iframe.")
            Path("page_debug.html").write_text(iframe_html, encoding="utf-8")
            print("🔍 Saved iframe HTML to page_debug.html for inspection")
            exit()
    else:
        print("❌ jwpSources not found and no iframe detected.")
        Path("page_debug.html").write_text(html, encoding="utf-8")
        print("🔍 Saved HTML to page_debug.html for inspection")
        exit()

# ========================
# 3️⃣ Ambil DRM Widevine
# ========================
widevine_data = None
for item in sources:
    drm = item.get("drm", {})
    if "widevine" in drm:
        widevine_data = drm["widevine"]
        break

if not widevine_data:
    print("❌ Widevine DRM data not found")
else:
    output_data = {
        "url": widevine_data.get("url"),
        "header": {
            "name": widevine_data.get("headers", {}).get("name"),
            "value": widevine_data.get("headers", {}).get("value"),
        },
    }

    out_file = Path("jajan_kuekue.json")
    out_file.write_text(json.dumps(output_data, indent=2), encoding="utf-8")

    print(f"✅ Widevine license data saved → {out_file}")
    print(json.dumps(output_data, indent=2))
