#!/usr/bin/env bash

REPO_NAME="RENYAHKU"
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"
COOKIES_FILE="$HOME/cookies.txt"
URL_FILE="$HOME/urls_live.txt"
WORKDIR="$(pwd)"

# ================= UTIL =================

run_cmd() {
    "$@" 2>/dev/null
}

fetch_html() {
    curl -A "$USER_AGENT" -L -s --cookie "$COOKIES_FILE" "$1"
}

safe_filename() {
    echo "$1" | tr -cd '[:alnum:]_.-'
}

# ================= VIDEO ID =================

get_video_id() {
    local url="$1"
    local html vid data username

    # 1. canonical link
    html="$(fetch_html "$url")"
    vid="$(echo "$html" | grep -oP 'canonical" href="https://www.youtube.com/watch\?v=\K[A-Za-z0-9_-]{11}')"
    [[ -n "$vid" ]] && { echo "$vid"; return 0; }

    # 2. yt-dlp get-id
    vid="$(run_cmd yt-dlp --no-warnings --cookies "$COOKIES_FILE" --user-agent "$USER_AGENT" --get-id "$url")"
    [[ -n "$vid" ]] && { echo "$vid"; return 0; }

    # 3. @username/live
    if [[ "$url" =~ youtube\.com/@([^/]+) ]]; then
        username="${BASH_REMATCH[1]}"
        data="$(run_cmd yt-dlp --no-warnings --cookies "$COOKIES_FILE" --user-agent "$USER_AGENT" --dump-single-json "https://www.youtube.com/@${username}/live")"
        vid="$(echo "$data" | grep -oP '"id":\s*"\K[A-Za-z0-9_-]{11}' | head -n 1)"
        [[ -n "$vid" ]] && { echo "$vid"; return 0; }
    fi

    return 1
}

# ================= HLS =================
# YouTube LIVE tidak punya "master m3u8"
# Ambil HLS playlist terbaik yang tersedia

get_master_m3u8() {
    local url="$1"
    local out

    out="$(yt-dlp -4 \
        --no-warnings \
        --cookies "$COOKIES_FILE" \
        --user-agent "$USER_AGENT" \
        --extractor-args "youtube:player_client=android" \
        --hls-prefer-native \
        -g "$url" 2>/dev/null | head -n 1)"

    [[ "$out" == https://manifest.googlevideo.com/* ]] && echo "$out"
}

# ================= MAIN =================

[[ ! -f "$URL_FILE" ]] && { echo "[!] File $URL_FILE tidak ditemukan"; exit 1; }
command -v yt-dlp >/dev/null || { echo "[!] yt-dlp tidak ditemukan"; exit 1; }
command -v curl >/dev/null || { echo "[!] curl tidak ditemukan"; exit 1; }

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

    resolved_url="https://www.youtube.com/watch?v=$video_id"
    echo "[+] Resolved URL: $resolved_url"

    m3u8="$(get_master_m3u8 "$resolved_url")"
    [[ -z "$m3u8" || "$m3u8" != *".m3u8"* ]] && {
        echo "[!] Gagal ambil HLS: $resolved_url"
        continue
    }

    output_file="$WORKDIR/${safe}.m3u8.txt"
    echo "$m3u8" > "$output_file"
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
