#!/usr/bin/env bash

REPO_NAME="RENYAHKU"
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"
COOKIES_FILE="$HOME/cookies.txt"
URL_FILE="$HOME/urls_live.txt"
WORKDIR="$(pwd)"

# -----------------------------
#  AUTO REFRESH YOUTUBE COOKIES
# -----------------------------
refresh_cookies() {
    echo "[*] Refreshing YouTube cookies..."

    # >>> PATCH: gunakan watch?v untuk dapet VISITOR_INFO1_LIVE + YSC
    curl -s -A "$USER_AGENT" \
         -D "$COOKIES_FILE" \
         "https://www.youtube.com/watch?v=AAAAAAAAAAA" \
         -o /dev/null

    if grep -q "VISITOR_INFO1_LIVE" "$COOKIES_FILE"; then
        echo "[✓] Cookies refreshed → $COOKIES_FILE"
    else
        echo "[!] Cookie refresh FAILED — YouTube tidak mengirim cookie!"
        echo "[!] Script lanjut dengan cookie lama."
    fi
}

# -----------------------------
#  UTILITY
# -----------------------------
run_cmd() {
    "$@" 2>/dev/null
}

fetch_html() {
    curl -A "$USER_AGENT" -L -s --cookie "$COOKIES_FILE" "$1"
}

safe_filename() {
    echo "$1" | tr -cd '[:alnum:]_.-'
}

# -----------------------------
#  RESOLVE VIDEO ID
# -----------------------------
get_video_id() {
    local url="$1"
    local html vid data username

    echo "    [DBG] Resolve ID from: $url"

    # 1. Canonical link
    html="$(fetch_html "$url")"
    vid="$(echo "$html" | grep -oP 'canonical" href="https://www.youtube.com/watch\?v=\K[A-Za-z0-9_-]{11}')"

    if [[ -n "$vid" ]]; then
        echo "    [DBG] Canonical ID: $vid"
        echo "$vid"
        return 0
    fi

    # 2. yt-dlp direct
    vid="$(run_cmd yt-dlp --no-warnings --cookies "$COOKIES_FILE" --user-agent "$USER_AGENT" --get-id "$url")"

    if [[ -n "$vid" ]]; then
        echo "    [DBG] yt-dlp ID: $vid"
        echo "$vid"
        return 0
    fi

    # 3. @username/live
    if [[ "$url" =~ youtube\.com/@([^/]+) ]]; then
        username="${BASH_REMATCH[1]}"
        echo "    [DBG] Username detected: $username"

        data="$(run_cmd yt-dlp --no-warnings --cookies "$COOKIES_FILE" --user-agent "$USER_AGENT" "--dump-single-json" "ytsearch10:${username} live")"

        vid="$(echo "$data" | grep -oP '"id":\s*"\K[A-Za-z0-9_-]{11}' | head -n 1)"

        if [[ -n "$vid" ]]; then
            echo "    [DBG] ytsearch ID: $vid"
            echo "$vid"
            return 0
        fi
    fi

    echo "    [DBG] FAILED — no ID found"
    echo ""
    return 1
}

# -----------------------------
#  GET MASTER M3U8
# -----------------------------
get_master_m3u8() {
    local url="$1"
    local json master

    json="$(run_cmd yt-dlp \
        --no-warnings \
        --cookies "$COOKIES_FILE" \
        --user-agent "$USER_AGENT" \
        --dump-single-json \
        "$url")"

    master="$(echo "$json" | grep -oP '"url":\s*"\K[^"]+' | grep '\.m3u8' | head -n 1)"

    if [[ -n "$master" ]]; then
        echo "$master"
        return 0
    fi

    echo ""
    return 1
}

# =================================================
#  MAIN PROGRAM
# =================================================
refresh_cookies   # <<< PATCH — FRESH COOKIE BENAR

if [[ ! -f "$URL_FILE" ]]; then
    echo "[!] File $URL_FILE tidak ditemukan!"
    exit 1
fi

# Check dependency
if ! command -v yt-dlp &>/dev/null; then
    echo "[!] yt-dlp tidak ditemukan!"
    exit 1
fi

while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    [[ "$line" =~ ^[[:space:]]*# ]] && continue

    name=$(echo "$line" | awk '{print $1}')
    url=$(echo "$line" | sed 's/^[^ ]* //')

    safe=$(safe_filename "$name")

    echo "[*] Memproses: $name"

    # Resolve ID
    video_id=$(get_video_id "$url")

    if [[ -z "$video_id" ]]; then
        echo "[!] Tidak bisa resolve video ID untuk: $url"
        continue
    fi

    resolved_url="https://www.youtube.com/watch?v=$video_id"
    echo "    [+] Video ID: $video_id"

    # Grab master HLS
    m3u8=$(get_master_m3u8 "$resolved_url")

    if [[ -z "$m3u8" ]]; then
        echo "[!] Gagal ambil master HLS untuk: $resolved_url"
        continue
    fi

    output_file="$WORKDIR/${safe}.m3u8.txt"
    echo "$m3u8" > "$output_file"

    echo "[✓] Disimpan: $output_file"

done < "$URL_FILE"

# =================================================
#  GIT OPS
# =================================================

git config user.email "actions@github.com"
git config user.name "GitHub Actions"

git add .

if ! git diff --cached --quiet; then
    commit_msg="Update dari $REPO_NAME/bash2.sh - $(date '+%Y-%m-%d %H:%M:%S')"
    git commit -m "$commit_msg"

    git fetch origin master

    if git merge --strategy-option=theirs origin/master 2>/dev/null; then
        git push origin master
    else
        git push --force-with-lease origin master
    fi
else
    echo "[i] Tidak ada perubahan."
fi

echo "[✓] Script selesai"
