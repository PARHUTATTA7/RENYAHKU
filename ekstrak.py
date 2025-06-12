import requests
import re
import json
from html import unescape
from pathlib import Path

# Lokasi file input
URL_FILE = Path.home() / "page_url.txt"

with open(URL_FILE) as f:
    page_url = f.read().strip()

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"
}

resp = requests.get(page_url, headers=headers)
html = resp.text

# Cari blok jwpSources
match = re.search(r'jwpSources\s*=\s*(\[\{.*?\}\])\s*,', html, re.DOTALL)
if not match:
    print("❌ jwpSources not found")
else:
    raw_json = match.group(1).replace('\\/', '/')
    raw_json = unescape(raw_json)

    try:
        sources = json.loads(raw_json)
        widevine_data = None

        for item in sources:
            drm = item.get("drm", {})
            if "widevine" in drm:
                widevine_data = drm["widevine"]
                break

        if widevine_data:
            print("✅ Widevine data found")

            # Format hasil ke dalam bentuk dict JSON
            output_data = {
                "url": widevine_data["url"],
                "header": {
                    "name": widevine_data["headers"]["name"],
                    "value": widevine_data["headers"]["value"]
                }
            }

            with open("jajan_kuekue.json", "w") as out:
                json.dump(output_data, out, indent=2)
        else:
            print("❌ No Widevine DRM found in jwpSources")

    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
