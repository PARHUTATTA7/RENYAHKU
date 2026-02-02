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

# ================= GET LIVE STREAM URL =================
# Khusus untuk YouTube live streaming

get_live_stream_url() {
    local url="$1"
    local stream_url
    
    # Method 1: Coba format live stream khusus
    stream_url="$(run_cmd yt-dlp \
        --no-warnings \
        --cookies "$COOKIES_FILE" \
        --user-agent "$USER_AGENT" \
        --live-from-start \
        -f "best[format_id*=91]/best[height<=720]/best" \
        -g "$url" 2>/dev/null | head -n 1)"
    
    [[ -n "$stream_url" ]] && { echo "$stream_url"; return 0; }
    
    # Method 2: Coba format lainnya
    stream_url="$(run_cmd yt-dlp \
        --no-warnings \
        --cookies "$COOKIES_FILE" \
        --user-agent "$USER_AGENT" \
        -f "best" \
        -g "$url" 2>/dev/null | head -n 1)"
    
    [[ -n "$stream_url" ]] && { echo "$stream_url"; return 0; }
    
    # Method 3: Coba dengan format yang lebih spesifik
    stream_url="$(run_cmd yt-dlp \
        --no-warnings \
        --cookies "$COOKIES_FILE" \
        --user-agent "$USER_AGENT" \
        --format "bestvideo+bestaudio/best" \
        -g "$url" 2>/dev/null | head -n 1)"
    
    echo "$stream_url"
}

# ================= CHECK IF LIVE =================

check_if_live() {
    local url="$1"
    local status
    
    # Cek apakah video sedang live
    status="$(run_cmd yt-dlp --no-warnings --cookies "$COOKIES_FILE" \
        --user-agent "$USER_AGENT" --dump-json "$url" 2>/dev/null | \
        grep -o '"is_live":\s*true' | head -n 1)"
    
    if [[ -n "$status" ]]; then
        echo "[+] Video sedang LIVE"
        return 0
    else
        echo "[-] Video TIDAK sedang live"
        return 1
    fi
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
    
    # Cek status live
    if ! check_if_live "$resolved_url"; then
        echo "[!] Video tidak sedang live, skip..."
        continue
    fi

    stream_url="$(get_live_stream_url "$resolved_url")"
    [[ -z "$stream_url" ]] && {
        echo "[!] Gagal ambil stream URL: $resolved_url"
        # Debug: coba lihat informasi lengkap
        echo "[*] Debug info:"
        run_cmd yt-dlp --no-warnings --cookies "$COOKIES_FILE" --user-agent "$USER_AGENT" -F "$resolved_url"
        continue
    }

    # Cek apakah URL valid (mengandung http)
    if [[ "$stream_url" != http* ]]; then
        echo "[!] Stream URL tidak valid: $stream_url"
        continue
    fi
    
    echo "[+] Berhasil dapat stream URL"
    echo "[*] Stream URL: ${stream_url:0:80}..."

    # Simpan URL stream ke file
    output_file="$WORKDIR/${safe}.txt"
    echo "$stream_url" > "$output_file"
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
