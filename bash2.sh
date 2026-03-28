#!/usr/bin/env bash

REPO_NAME="RENYAHKU"
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"
COOKIES_FILE="$HOME/cookies.txt"
URL_FILE="$HOME/urls_live.txt"
API_FILE="$HOME/base_api.txt"
WORKDIR="$(pwd)"

# ================= UTIL =================

fetch_html() {
    curl -A "$USER_AGENT" -L -s --cookie "$COOKIES_FILE" "$1"
}

safe_filename() {
    echo "$1" | tr -cd '[:alnum:]_.-'
}

log() {
    echo "$1" >&2
}

# ================= MASKING =================

mask_id() {
    echo "***********"
}

mask_url() {
    echo "$1" | sed -E 's/(id=)[^&]+/\1***********/g'
}

mask_final_url() {
    echo "$1" \
        | sed -E 's/(id=)[^&]+/\1***********/g' \
        | sed -E 's/(sig=)[^\/]+/\1***/g' \
        | sed -E 's/(expire=)[0-9]+/\1***/g' \
        | sed -E 's/(ip=)[0-9\.]+/\1***/g'
}

# ================= LOAD API BASE =================

load_api_base() {
    [[ ! -f "$API_FILE" ]] && { log "[!] File API tidak ditemukan: $API_FILE"; exit 1; }

    API_BASE="$(head -n 1 "$API_FILE" | tr -d '\r\n')"

    [[ -z "$API_BASE" ]] && { log "[!] API_BASE kosong di file: $API_FILE"; exit 1; }

    log "[+] API_BASE loaded"
}

# ================= VIDEO ID EXTRACTOR =================

get_video_id() {
    local url="$1"
    local html vid

    if [[ "$url" =~ v=([A-Za-z0-9_-]{11}) ]]; then
        printf "%s" "${BASH_REMATCH[1]}"; return 0
    fi

    if [[ "$url" =~ youtu\.be/([A-Za-z0-9_-]{11}) ]]; then
        printf "%s" "${BASH_REMATCH[1]}"; return 0
    fi

    if [[ "$url" =~ youtube\.com/live/([A-Za-z0-9_-]{11}) ]]; then
        printf "%s" "${BASH_REMATCH[1]}"; return 0
    fi

    if [[ "$url" =~ youtube\.com/shorts/([A-Za-z0-9_-]{11}) ]]; then
        printf "%s" "${BASH_REMATCH[1]}"; return 0
    fi

    if [[ "$url" =~ youtube\.com/embed/([A-Za-z0-9_-]{11}) ]]; then
        printf "%s" "${BASH_REMATCH[1]}"; return 0
    fi

    html="$(fetch_html "$url")"

    vid="$(echo "$html" | grep -oPm1 'canonical" href="https://www\.youtube\.com/watch\?v=\K[A-Za-z0-9_-]{11}')"
    [[ -n "$vid" ]] && { printf "%s" "$vid"; return 0; }

    vid="$(echo "$html" | grep -oPm1 '"videoId":"\K[A-Za-z0-9_-]{11}')"
    [[ -n "$vid" ]] && { printf "%s" "$vid"; return 0; }

    vid="$(echo "$html" | grep -oPm1 'watch\?v=\K[A-Za-z0-9_-]{11}')"
    [[ -n "$vid" ]] && { printf "%s" "$vid"; return 0; }

    return 1
}

# ================= GET M3U8 =================

get_m3u8_from_api() {
    local video_id="$1"
    local api_url="${API_BASE}${video_id}"

    log "[*] Request API: $(mask_url "$api_url")"

    local final_url
    final_url=$(curl -A "$USER_AGENT" \
        -H "Accept: */*" \
        -H "Connection: keep-alive" \
        --max-redirs 10 \
        --connect-timeout 10 \
        -L -s -o /dev/null \
        -w '%{url_effective}' \
        "$api_url")

    log "[DEBUG] Final URL: $(mask_final_url "$final_url")"

    if [[ "$final_url" =~ ^https://manifest\.googlevideo\.com/.*\.m3u8 ]]; then
        printf "%s" "$final_url"
        return 0
    fi

    log "[!] Gagal mendapatkan redirect URL"
    return 1
}

# ================= MAIN =================

[[ ! -f "$URL_FILE" ]] && { log "[!] File $URL_FILE tidak ditemukan"; exit 1; }
command -v curl >/dev/null || { log "[!] curl tidak ditemukan"; exit 1; }

load_api_base

while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    [[ "$line" =~ ^[[:space:]]*# ]] && continue

    name="$(echo "$line" | awk '{print $1}')"
    url="$(echo "$line" | sed 's/^[[:space:]]*[^[:space:]]*[[:space:]]*//')"

    [[ -z "$name" || -z "$url" ]] && { log "[!] Format tidak valid"; continue; }

    safe="$(safe_filename "$name")"

    log "========================================"
    log "[*] Memproses: $name"

    video_id="$(get_video_id "$url")"
    [[ -z "$video_id" ]] && { log "[!] Gagal resolve video ID"; continue; }

    log "[+] Video ID: $(mask_id "$video_id")"

    m3u8="$(get_m3u8_from_api "$video_id")"
    [[ -z "$m3u8" ]] && { log "[!] API gagal kasih stream untuk ID: $(mask_id "$video_id")"; continue; }

    output_file="$WORKDIR/${safe}.m3u8.txt"

    printf "%s\n" "$m3u8" > "$output_file"

    log "[✓] Disimpan: $output_file"

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
    log "[✓] Berhasil push ke repository"
else
    log "[i] Tidak ada perubahan"
fi

log "[✓] Script selesai"
