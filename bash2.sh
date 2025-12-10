#!/usr/bin/env bash

REPO_NAME="RENYAHKU"
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"
COOKIES_FILE="$HOME/cookies.txt"
URL_FILE="$HOME/urls_live.txt"
WORKDIR="$(pwd)"

run_cmd() {
    "$@" 2>/dev/null
}

fetch_html() {
    curl -A "$USER_AGENT" -L -s --cookie "$COOKIES_FILE" "$1"
}

safe_filename() {
    echo "$1" | tr -cd '[:alnum:]_.-'
}

# ==========================================================
#  FIXED get_video_id → ambil dari ytInitialPlayerResponse
# ==========================================================
get_video_id() {
    local url="$1"

    html="$(fetch_html "$url")"

    # Ambil videoId dari ytInitialPlayerResponse (Paling akurat)
    vid="$(echo "$html" | grep -oP '"videoId":"\K[A-Za-z0-9_-]{11}' | head -n 1)"

    if [[ -n "$vid" ]]; then
        echo "$vid"
        return
    fi

    # Fallback via yt-dlp
    vid="$(run_cmd yt-dlp --no-warnings --cookies "$COOKIES_FILE" --user-agent "$USER_AGENT" --get-id "$url")"
    if [[ -n "$vid" ]]; then
        echo "$vid"
        return
    fi

    echo ""
}

# ==========================================================
#  FIXED get_master_m3u8 → Ambil hlsManifestUrl
# ==========================================================
get_master_m3u8() {
    local url="$1"

    # 1. Cara utama: pakai format hls
    master="$(run_cmd yt-dlp -g -f "hls" --cookies "$COOKIES_FILE" --user-agent "$USER_AGENT" "$url")"
    if [[ -n "$master" ]]; then
        echo "$master"
        return
    fi

    # 2. Fallback: semua tipe HLS
    master="$(run_cmd yt-dlp -g -f "hls-144,hls-240,hls-360,hls-480,hls-720,hls-1080" \
        --cookies "$COOKIES_FILE" --user-agent "$USER_AGENT" "$url")"
    if [[ -n "$master" ]]; then
        echo "$master"
        return
    fi

    # 3. Fallback terakhir: best (yt-dlp otomatis ambil manifest HLS)
    master="$(run_cmd yt-dlp -g -f best --cookies "$COOKIES_FILE" --user-agent "$USER_AGENT" "$url")"
    if [[ -n "$master" ]]; then
        echo "$master"
        return
    fi

    echo ""
}

### MAIN ###
if [[ ! -f "$URL_FILE" ]]; then
    echo "[!] File $URL_FILE tidak ditemukan!"
    exit 1
fi

while read -r line; do
    [[ -z "$line" || "$line" =~ ^# ]] && continue

    name=$(echo "$line" | awk '{print $1}')
    url=$(echo "$line" | cut -d" " -f2-)
    safe=$(safe_filename "$name")

    echo "[*] Memproses: $name"

    video_id=$(get_video_id "$url")

    if [[ -z "$video_id" ]]; then
        echo "[!] Tidak bisa resolve video ID untuk: $url"
        continue
    fi

    resolved_url="https://www.youtube.com/watch?v=$video_id"

    m3u8=$(get_master_m3u8 "$resolved_url")

    if [[ -z "$m3u8" ]]; then
        echo "[!] Gagal ambil master HLS untuk: $resolved_url"
        continue
    fi

    echo "$m3u8" > "$WORKDIR/${safe}.m3u8.txt"
    echo "[✓] Disimpan: ${safe}.m3u8.txt"

done < "$URL_FILE"

### GIT OPS ###
git config user.email "actions@github.com"
git config user.name "GitHub Actions"

git add .

if ! git diff --cached --quiet; then
    git commit -m "Update dari $REPO_NAME/bash2.sh - $(date '+%Y-%m-%d %H:%M:%S')"
fi

git fetch origin master
git merge --strategy=ours origin/master
git push origin master
