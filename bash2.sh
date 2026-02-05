#!/usr/bin/env bash

REPO_NAME="RENYAHKU"
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"
COOKIES_FILE="$HOME/cookies.txt"
URL_FILE="$HOME/urls_live.txt"
API_FILE="$HOME/base_api.txt"
WORKDIR="$(pwd)"

# ================= UTIL =================

safe_filename() {
    echo "$1" | tr -cd '[:alnum:]_.-'
}

curl_get() {
    curl -A "$USER_AGENT" -L -s \
        --retry 1 \
        --connect-timeout 5 \
        --max-time 12 \
        "$1" | tr -d '\000' | tr -d '\r'
}

fetch_html() {
    curl -A "$USER_AGENT" -L -s \
        --connect-timeout 5 \
        --max-time 12 \
        --cookie "$COOKIES_FILE" \
        "$1" | tr -d '\000' | tr -d '\r'
}

# ================= LOAD API BASE =================

load_api_base() {
    [[ ! -f "$API_FILE" ]] && { echo "[!] File API tidak ditemukan: $API_FILE"; exit 1; }

    API_BASE="$(head -n 1 "$API_FILE" | tr -d '\r\n')"
    [[ -z "$API_BASE" ]] && { echo "[!] API_BASE kosong di file: $API_FILE"; exit 1; }

    echo "[+] API_BASE loaded"
}

# ================= VIDEO ID EXTRACTOR =================

get_video_id() {
    local url="$1"
    local html vid

    if [[ "$url" =~ v=([A-Za-z0-9_-]{11}) ]]; then
        echo "${BASH_REMATCH[1]}"; return 0
    fi
    if [[ "$url" =~ youtu\.be/([A-Za-z0-9_-]{11}) ]]; then
        echo "${BASH_REMATCH[1]}"; return 0
    fi
    if [[ "$url" =~ youtube\.com/live/([A-Za-z0-9_-]{11}) ]]; then
        echo "${BASH_REMATCH[1]}"; return 0
    fi
    if [[ "$url" =~ youtube\.com/shorts/([A-Za-z0-9_-]{11}) ]]; then
        echo "${BASH_REMATCH[1]}"; return 0
    fi
    if [[ "$url" =~ youtube\.com/embed/([A-Za-z0-9_-]{11}) ]]; then
        echo "${BASH_REMATCH[1]}"; return 0
    fi

    html="$(fetch_html "$url")"

    vid="$(echo "$html" | grep -oP '"videoId":"\K[A-Za-z0-9_-]{11}' | sed -n '1p')"
    [[ -n "$vid" ]] && { echo "$vid"; return 0; }

    vid="$(echo "$html" | grep -oP 'watch\?v=\K[A-Za-z0-9_-]{11}' | sed -n '1p')"
    [[ -n "$vid" ]] && { echo "$vid"; return 0; }

    return 1
}

# ================= GET SINGLE M3U8 FROM API (FAST) =================

get_m3u8_from_api() {
    local video_id="$1"
    local api_url="${API_BASE}${video_id}"
    local api_text url

    api_text="$(curl_get "$api_url")"
    [[ -z "$api_text" ]] && return 1

    # kalau API sudah langsung ngasih URL doang
    if echo "$api_text" | grep -q "^https://manifest\.googlevideo\.com/api/manifest/"; then
        echo "$api_text" | head -n 1
        return 0
    fi

    # cari link hls_variant dulu
    url="$(echo "$api_text" | grep -aoE 'https://manifest\.googlevideo\.com/api/manifest/[^"[:space:]]+' | grep -m 1 "hls_variant")"
    [[ -n "$url" ]] && { echo "$url"; return 0; }

    # fallback cari link googlevideo manifest pertama
    url="$(echo "$api_text" | grep -aoE 'https://manifest\.googlevideo\.com/api/manifest/[^"[:space:]]+' | sed -n '1p')"
    [[ -n "$url" ]] && { echo "$url"; return 0; }

    return 1
}

# ================= MAIN =================

[[ ! -f "$URL_FILE" ]] && { echo "[!] File $URL_FILE tidak ditemukan"; exit 1; }
command -v curl >/dev/null || { echo "[!] curl tidak ditemukan"; exit 1; }

load_api_base

while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    [[ "$line" =~ ^[[:space:]]*# ]] && continue

    name="$(echo "$line" | awk '{print $1}')"
    url="$(echo "$line" | sed 's/^[[:space:]]*[^[:space:]]*[[:space:]]*//')"

    [[ -z "$name" || -z "$url" ]] && { echo "[!] Format tidak valid: $line"; continue; }

    safe="$(safe_filename "$name")"
    echo "[*] Memproses: $name"

    video_id="$(get_video_id "$url")"
    [[ -z "$video_id" ]] && { echo "[!] Gagal resolve video ID"; continue; }

    echo "[+] Video ID: $video_id"

    m3u8_url="$(get_m3u8_from_api "$video_id")"
    [[ -z "$m3u8_url" ]] && { echo "[!] API gagal kasih manifest untuk ID: $video_id"; continue; }

    output_file="$WORKDIR/${safe}.m3u8.txt"
    echo "$m3u8_url" > "$output_file"

    echo "[✓] Disimpan: $output_file"
done < "$URL_FILE"

# ================= GIT =================

git config user.email "actions@github.com"
git config user.name "GitHub Actions"

git add .

if ! git diff --cached --quiet; then
    git commit -m "Update dari $REPO_NAME/bash2.sh - $(date '+%Y-%m-%d %H:%M:%S')"
    git fetch origin master
    git merge --strategy-option=theirs origin/master 2>/dev/null || true
    git push origin master --force-with-lease
    echo "[✓] Berhasil push ke repository"
else
    echo "[i] Tidak ada perubahan"
fi

echo "[✓] Script selesai"
