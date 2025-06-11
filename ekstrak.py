import requests, re, json
from html import unescape
from pathlib import Path

URL_FILE = Path.home() / "page_url.txt"
with open(URL_FILE) as f:
    page_url = f.read().strip()

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"
}
resp = requests.get(page_url, headers=headers)
html = resp.text

match = re.search(r'jwpSources\s*=\s*(\[\{.*?\}\])\s*,', html, re.DOTALL)
if not match:
    print("❌ jwpSources not found")
else:
    raw_json = match.group(1).replace('\\/', '/')
    raw_json = unescape(raw_json)

    try:
        sources = json.loads(raw_json)
        found = False

        for item in sources:
            drm = item.get("drm", {})
            if "widevine" in drm:
                widevine_data = drm["widevine"]
                found = True
                break

        if found:
            print("✅ Widevine data found")
            with open("drm_widevine.txt", "w") as out:
                out.write("URL:\n" + widevine_data["url"] + "\n\n")
                out.write("Header Name:\n" + widevine_data["headers"]["name"] + "\n\n")
                out.write("Header Value:\n" + widevine_data["headers"]["value"] + "\n")
        else:
            print("❌ No Widevine DRM found in jwpSources")

    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
