import requests
import re
import json
from html import unescape
from pathlib import Path
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Lokasi file input
URL_FILE = Path.home() / "page_url.txt"

with open(URL_FILE, encoding="utf-8") as f:
    page_url = f.read().strip()

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

try:
    # Ambil halaman
    resp = requests.get(page_url, headers=headers, verify=False, timeout=20)
    html = resp.text

    # Tangkap seluruh blok jwpSources = [...]
    match = re.search(r'jwpSources\s*=\s*(\[[\s\S]*?\])\s*,\s*\n\s*drmToken', html)
    if not match:
        print("❌ jwpSources not found")
        Path("page_debug.html").write_text(html, encoding="utf-8")
        print("🔍 Saved HTML to page_debug.html for inspection")
    else:
        raw_json = match.group(1)
        # Bersihkan escape agar valid JSON
        raw_json = raw_json.encode("utf-8").decode("unicode_escape")
        raw_json = raw_json.replace("\\/", "/")
        raw_json = unescape(raw_json)

        try:
            sources = json.loads(raw_json)
            widevine_data = None

            # Ambil DRM Widevine pertama yang ditemukan
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
                        "value": widevine_data.get("headers", {}).get("value")
                    }
                }

                # Simpan ke file JSON
                out_file = Path("jajan_kuekue.json")
                out_file.write_text(json.dumps(output_data, indent=2), encoding="utf-8")

                print(f"✅ Widevine license data saved → {out_file}")
                print(json.dumps(output_data, indent=2))

        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}")
            Path("raw_jwpSources.txt").write_text(raw_json, encoding="utf-8")
            print("🔍 Saved raw JSON to raw_jwpSources.txt for debugging")

except requests.exceptions.RequestException as e:
    print(f"❌ Request error: {e}")
