#!/usr/bin/env bash

set -u

REPO_NAME="RENYAHKU"
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"
COOKIES_FILE="$HOME/cookies.txt"
URL_FILE="$HOME/urls_live.txt"
WORKDIR="$(pwd)"
ERRLOG="/tmp/yt_err.log"

run_cmd() {
    "$@" 2>>"$ERRLOG"
}

fetch_html() {
    curl -A "$USER_AGENT" -L -s --cookie "$COOKIES_FILE" "$1"
}

safe_filename() {
    echo "$1" | tr -cd '[:alnum:]_.-'
}

# =========================
# RESOLVE VIDEO ID
# =========================
get_video_id() {
    local url="$1"
    local html vid

    html="$(fetch_html "$url")"
    vid="$(echo "$html" | grep -oP 'watch\?v=\K[A-Za-z0-9_-]{11}' | head -n 1)"
    [[ -n "$vid" ]] && echo "$vid" && return 0

    vid="$(run_cmd yt-dlp --no-warnings \
        --cookies "$COOKIES_FILE" \
        --user-agent "$USER_AGENT" \
        --get-id "$url")"
    [[ -n "$vid" ]] && echo "$vid" && return 0

    if [[ "$url" =~ youtube\.com/@([^/]+) ]]; then
        local user="${BASH_REMATCH[1]}"
        vid="$(run_cmd yt-dlp --no-warnings \
            --cookies "$COOKIES_FILE" \
            --user-agent "$USER_AGENT" \
            --dump-single-json "ytsearch1:${user} live" \
            | grep -oP '"id":\s*"\K[A-Za-z0-9_-]{11}' | head -n 1)"
        [[ -n "$vid" ]] && echo "$vid" && return 0
    fi

    return 1
}

# =========================
# GET HLS URL (LIVE SAFE)
# return:
#   0 = success
#   1 = no hls
#   2 = login required
# =========================
get_master_m3u8() {
    local url="$1"
    local best_id hls

    : > "$ERRLOG"

    # 1️⃣ Cari format HLS TANPA cookies
    best_id="$(yt-dlp -F "$url" 2>/dev/null \
        | awk '$0 ~ /m3u8/ {print $1}' \
        | sort -n | tail -n 1)"

    [[ -z "$best_id" ]] && return 1

    # 2️⃣ Ambil URL stream (pakai cookies)
    hls="$(yt-dlp \
        --no-warnings \
        --cookies "$COOKIES_FILE" \
        --user-agent "$USER_AGENT" \
        -g \
        -f "$best_id" \
        "$url" 2>>"$ERRLOG")"

    if grep -qiE "Sign in|confirm you.?re not a bot" "$ERRLOG"; then
        return 2
    fi

    [[ -n "$hls" && "$hls" == *".m3u8"* ]] && echo "$hls" && return 0
    return 1
}

# =========================
# MAIN
# =========================
[[ ! -f "$URL_FILE" ]] && { echo "[!] File $URL_FILE tidak ditemukan"; exit 1; }
command -v yt-dlp >/dev/null || { echo "[!] yt-dlp belum terinstall"; exit 1; }
command -v curl >/dev/null || { echo "[!] curl belum terinstall"; exit 1; }

while IFS= read -r line; do
    [[ -z "$line" || "$line" =~ ^[[:space:]]*# ]] && continue

    name="$(echo "$line" | awk '{print $1}')"
    url="$(echo "$line" | sed 's/^[^ ]* //')"
    [[ -z "$name" || -z "$url" ]] && continue

    safe="$(safe_filename "$name")"
    echo "[*] Memproses: $name"

    vid="$(get_video_id "$url")"
    [[ -z "$vid" ]] && { echo "[!] Gagal resolve ID"; continue; }

    resolved="https://www.youtube.com/watch?v=$vid"
    echo "[+] Resolved URL: $resolved"

    m3u8="$(get_master_m3u8 "$resolved")"
    status=$?

    if [[ $status -eq 2 ]]; then
        echo "[!] LOGIN REQUIRED (cookies expired / bot check)"
        continue
    elif [[ -z "$m3u8" ]]; then
        echo "[!] HLS tidak tersedia (LIVE belum aktif?)"
        continue
    fi

    outfile="$WORKDIR/${safe}.m3u8.txt"
    echo "$m3u8" > "$outfile"
    echo "[✓] Disimpan: $outfile"

done < "$URL_FILE"

# =========================
# GIT
# =========================
git config user.email "actions@github.com"
git config user.name "GitHub Actions"

git add .
if ! git diff --cached --quiet; then
    git commit -m "Update $REPO_NAME - $(date '+%Y-%m-%d %H:%M:%S')"
    git fetch origin master
    git merge --strategy-option=theirs origin/master 2>/dev/null || true
    git push --force-with-lease origin master
fi

echo "[✓] Script selesai"
