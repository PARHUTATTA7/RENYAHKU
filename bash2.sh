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

get_video_id() {
    local url="$1"

    # 1. Ambil canonical link dari HTML
    html="$(fetch_html "$url")"
    vid="$(echo "$html" | grep -oP 'canonical" href="https://www.youtube.com/watch\?v=\K[A-Za-z0-9_-]{11}')"

    if [[ -n "$vid" ]]; then
        echo "$vid"
        return
    fi

    # 2. Ambil ID via yt-dlp
    vid="$(run_cmd yt-dlp --no-warnings --cookies "$COOKIES_FILE" --user-agent "$USER_AGENT" --get-id "$url")"

    if [[ -n "$vid" ]]; then
        echo "$vid"
        return
    fi

    # 3. Jika URL-nya @username/live → cari via ytsearch
    if [[ "$url" =~ youtube\.com/@([^/]+) ]]; then
        username="${BASH_REMATCH[1]}"
        data="$(run_cmd yt-dlp --no-warnings --cookies "$COOKIES_FILE" --user-agent "$USER_AGENT" --dump-single-json "ytsearch5:${username} live")"

        vid="$(echo "$data" | jq -r '.entries[] | select(.live_status=="is_live" or .live_status=="live") | .id' 2>/dev/null | head -n 1)"

        if [[ -n "$vid" ]]; then
            echo "$vid"
            return
        fi
    fi

    echo ""
}

get_master_m3u8() {
    url="$1"

    manifest="$(run_cmd yt-dlp \
        --no-warnings \
        --cookies "$COOKIES_FILE" \
        --user-agent "$USER_AGENT" \
        --print "%(manifest_url)s" \
        "$url"
    )"

    if [[ "$manifest" == http* && "$manifest" == *m3u8* ]]; then
        echo "$manifest"
    else
        echo ""
    fi
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
