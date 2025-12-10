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
    curl -A "$USER_AGENT" -L -s "$1"
}

safe_filename() {
    echo "$1" | tr -cd '[:alnum:]_.-'
}

# ==========================================================
#  jika URL sudah mengandung video ID, langsung return ID
# ==========================================================
extract_id_if_exists() {
    local url="$1"

    # Cek pola ?v=ID
    if [[ "$url" =~ v=([A-Za-z0-9_-]{11}) ]]; then
        echo "${BASH_REMATCH[1]}"
        return 0
    fi

    # Cek pola /shorts/ID
    if [[ "$url" =~ shorts/([A-Za-z0-9_-]{11}) ]]; then
        echo "${BASH_REMATCH[1]}"
        return 0
    fi

    # Cek pola /live/ID
    if [[ "$url" =~ live/([A-Za-z0-9_-]{11}) ]]; then
        echo "${BASH_REMATCH[1]}"
        return 0
    fi

    return 1
}

# ==========================================================
#  get_video_id — untuk URL channel atau live redirect
# ==========================================================
get_video_id() {
    local url="$1"

    # 1️⃣ Coba cek apakah URL sudah punya ID → skip pencarian
    video_id="$(extract_id_if_exists "$url")"
    if [[ -n "$video_id" ]]; then
        echo "$video_id"
        return
    fi

    # 2️⃣ Ambil via HTML ytInitialPlayerResponse
    html="$(fetch_html "$url")"
    vid="$(echo "$html" | grep -oP '"videoId":"\K[A-Za-z0-9_-]{11}' | head -n 1)"

    if [[ -n "$vid" ]]; then
        echo "$vid"
        return
    fi

    # 3️⃣ Fallback yt-dlp
    vid="$(run_cmd yt-dlp --no-warnings --get-id "$url")"
    if [[ -n "$vid" ]]; then
        echo "$vid"
        return
    fi

    echo ""
}

# ==========================================================
#  get_master_m3u8 — ambil manifest YouTube LIVE
# ==========================================================
get_master_m3u8() {
    local url="$1"

    master=$(yt-dlp -g \
        --cookies "$COOKIES_FILE" \
        --no-warnings \
        "$url" 2>/dev/null)

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
