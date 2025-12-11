#!/usr/bin/env bash

REPO_NAME="RENYAHKU"
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"
URL_FILE="$HOME/urls_live.txt"
WORKDIR="$(pwd)"

run_cmd() { "$@" 2>/dev/null; }

fetch_html() {
    curl -A "$USER_AGENT" -L -s "$1"
}

safe_filename() {
    echo "$1" | tr -cd '[:alnum:]_.-'
}

# ==========================================================
# 1. RESOLVE VIDEO ID LANGSUNG DARI YOUTUBE
# ==========================================================
get_video_id() {
    local url="$1"

    # 1. Ambil HTML
    html="$(fetch_html "$url")"

    # --- A. Cek canonical langsung ---
    vid="$(echo "$html" | grep -oP 'canonical" href="https://www.youtube.com/watch\?v=\K[A-Za-z0-9_-]{11}')"
    if [[ -n "$vid" ]]; then
        echo "$vid"
        return
    fi

    # --- B. Cek currentVideoEndpoint (halaman /@user/live) ---
    vid="$(echo "$html" | grep -oP '"currentVideoEndpoint":\s*\{"videoId":\s*"\K[A-Za-z0-9_-]{11}')"
    if [[ -n "$vid" ]]; then
        echo "$vid"
        return
    fi

    # --- C. Pakai yt-dlp dump JSON (AMUNISI TERAKHIR yang paling akurat) ---
    json="$(run_cmd yt-dlp --no-warnings --dump-single-json "$url")"
    vid="$(echo "$json" | grep -oP '"currentVideoEndpoint":.*"videoId":\s*"\K[A-Za-z0-9_-]{11}')"
    if [[ -n "$vid" ]]; then
        echo "$vid"
        return
    fi

    # --- D. Fallback: cari di search ---
    if [[ "$url" =~ youtube\.com/@([^/]+) ]]; then
        username="${BASH_REMATCH[1]}"
        json2="$(run_cmd yt-dlp --no-warnings --dump-single-json "ytsearch5:${username} live")"
        vid="$(echo "$json2" | grep -oP '"id":\s*"\K[A-Za-z0-9_-]{11}' | head -n 1)"
        if [[ -n "$vid" ]]; then
            echo "$vid"
            return
        fi
    fi

    echo ""
}

# ==========================================================
# 2. AMBIL MASTER M3U8 DARI INVIDIOUS (TANPA COOKIE)
# ==========================================================
get_master_m3u8_invidious() {
    local video_id="$1"
    local embed_url="https://invidious.nerdvpn.de/embed/${video_id}"

    m3u8="$(run_cmd yt-dlp \
        --no-warnings \
        --user-agent "$USER_AGENT" \
        -g "$embed_url")"

    if [[ -n "$m3u8" ]]; then
        echo "$m3u8"
        return
    fi

    echo ""
}

# ==========================================================
# MAIN
# ==========================================================
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
        echo "[!] Tidak bisa resolve video ID: $url"
        continue
    fi

    echo "    → Video ID: $video_id"

    # Ambil M3U8 via Invidious
    m3u8=$(get_master_m3u8_invidious "$video_id")
    if [[ -z "$m3u8" ]]; then
        echo "[!] Gagal ambil master HLS via Invidious!"
        continue
    fi

    echo "$m3u8" > "$WORKDIR/${safe}.m3u8.txt"
    echo "[✓] Disimpan: ${safe}.m3u8.txt"

done < "$URL_FILE"

# ==========================================================
# GIT OPS
# ==========================================================
git config user.email "actions@github.com"
git config user.name "GitHub Actions"

git add .
if ! git diff --cached --quiet; then
    git commit -m "Update dari $REPO_NAME/bash2.sh - $(date '+%Y-%m-%d %H:%M:%S')"
fi

git fetch origin master
git merge --strategy=ours origin/master
git push origin master
