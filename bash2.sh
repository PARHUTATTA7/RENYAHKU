#!/usr/bin/env bash

REPO_NAME="RENYAHKU"
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"
COOKIES_FILE="$HOME/cookies.txt"
URL_FILE="$HOME/urls_live.txt"
API_FILE="$HOME/base_api.txt"
WORKDIR="$(pwd)"

# ================= UTIL =================

curl_get() {
    curl -A "$USER_AGENT" -L -s --retry 2 --connect-timeout 5 --max-time 15 "$@" \
        | tr -d '\000' \
        | tr -d '\r'
}

# ================= LOAD API BASE =================

load_api_base() {
    [[ ! -f "$API_FILE" ]] && { echo "[!] File API tidak ditemukan: $API_FILE"; exit 1; }
    API_BASE="$(head -n 1 "$API_FILE" | tr -d '\r\n')"
    [[ -z "$API_BASE" ]] && { echo "[!] API_BASE kosong di file: $API_FILE"; exit 1; }
    echo "[+] API_BASE loaded"
}

# ================= FAST VIDEO ID EXTRACTOR =================

get_video_id() {
    local url="$1"
    
    # Regex langsung tanpa cek HTML untuk URL umum
    if [[ "$url" =~ v=([A-Za-z0-9_-]{11}) ]]; then
        echo "${BASH_REMATCH[1]}"
    elif [[ "$url" =~ youtu\.be/([A-Za-z0-9_-]{11}) ]]; then
        echo "${BASH_REMATCH[1]}"
    elif [[ "$url" =~ youtube\.com/live/([A-Za-z0-9_-]{11}) ]]; then
        echo "${BASH_REMATCH[1]}"
    elif [[ "$url" =~ youtube\.com/shorts/([A-Za-z0-9_-]{11}) ]]; then
        echo "${BASH_REMATCH[1]}"
    elif [[ "$url" =~ youtube\.com/embed/([A-Za-z0-9_-]{11}) ]]; then
        echo "${BASH_REMATCH[1]}"
    else
        # Cepat ambil hanya bagian akhir URL yang mungkin ID
        echo "$url" | grep -oE '[A-Za-z0-9_-]{11}' | head -1
    fi
}

# ================= GET SINGLE M3U8 LINK FROM API =================

get_single_m3u8() {
    local video_id="$1"
    local api_url="${API_BASE}${video_id}"
    
    # Langsung grep link m3u8 dengan pattern hls_variant (tanpa parsing JSON kompleks)
    local m3u8_url
    m3u8_url="$(curl_get "$api_url" | grep -o 'https://manifest.googlevideo.com/api/manifest/hls_variant[^"]*' | head -1)"
    
    if [[ -n "$m3u8_url" ]]; then
        echo "$m3u8_url"
        return 0
    fi
    
    # Fallback cepat untuk m3u8 lain
    curl_get "$api_url" | grep -o 'https://[^"]*\.m3u8[^"]*' | head -1
}

# ================= MAIN PROCESSING =================

[[ ! -f "$URL_FILE" ]] && { echo "[!] File $URL_FILE tidak ditemukan"; exit 1; }
command -v curl >/dev/null || { echo "[!] curl tidak ditemukan"; exit 1; }

load_api_base

processed_count=0

# Gunakan while loop yang lebih efisien
while IFS= read -r line || [[ -n "$line" ]]; do
    # Skip kosong dan komentar
    [[ -z "${line// }" ]] && continue
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    
    # Parsing sederhana: ambil nama (kata pertama) dan URL (sisanya)
    name="${line%% *}"
    url="${line#* }"
    
    [[ -z "$name" || -z "$url" ]] && continue
    
    echo "[*] Processing: $name"
    
    # Ambil video ID dengan cepat
    video_id="$(get_video_id "$url")"
    if [[ -z "$video_id" ]]; then
        echo "[!] Failed to get video ID from: $url"
        continue
    fi
    
    echo "[+] Video ID: $video_id"
    
    # Ambil single m3u8 link langsung
    m3u8_url="$(get_single_m3u8 "$video_id")"
    if [[ -z "$m3u8_url" ]]; then
        echo "[!] No m3u8 link found for: $video_id"
        continue
    fi
    
    # Simpan langsung ke file
    echo "$m3u8_url" > "${WORKDIR}/${name}.m3u8.txt"
    
    echo "[✓] Saved: ${name}.m3u8.txt"
    echo "     URL: $(echo "$m3u8_url" | cut -c1-80)..."
    
    ((processed_count++))
    
    # Small delay to prevent rate limiting (optional)
    sleep 0.5
    
done < "$URL_FILE"

# ================= GIT UPDATE =================

echo "[+] Processed $processed_count URLs"

if [[ $processed_count -gt 0 ]]; then
    git config user.email "actions@github.com"
    git config user.name "GitHub Actions"
    
    git add *.m3u8.txt 2>/dev/null
    
    if ! git diff --cached --quiet; then
        git commit -m "Auto update m3u8 links - $(date '+%Y-%m-%d %H:%M:%S')"
        git push origin master --force-with-lease
        echo "[✓] Successfully pushed to repository"
    else
        echo "[i] No changes to commit"
    fi
fi

echo "[✓] Script completed in $(date +%s) seconds"
