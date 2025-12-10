#!/usr/bin/env bash

REPO_NAME="RENYAHKU"
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"
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

# ---------------------------------------------
# extract ID jika sudah ada di URL
# ---------------------------------------------
extract_id_if_exists() {
    local url="$1"

    if [[ "$url" =~ v=([A-Za-z0-9_-]{11}) ]]; then
        echo "${BASH_REMATCH[1]}"
        return 0
    fi

    if [[ "$url" =~ shorts/([A-Za-z0-9_-]{11}) ]]; then
        echo "${BASH_REMATCH[1]}"
        return 0
    fi

    if [[ "$url" =~ live/([A-Za-z0-9_-]{11}) ]]; then
        echo "${BASH_REMATCH[1]}"
        return 0
    fi

    return 1
}

# ---------------------------------------------
# Ambil video ID
# ---------------------------------------------
get_video_id() {
    local url="$1"

    video_id="$(extract_id_if_exists "$url")"
    if [[ -n "$video_id" ]]; then
        echo "$video_id"
        return
    fi

    html="$(fetch_html "$url")"
    vid="$(echo "$html" | grep -oP '"videoId":"\K[A-Za-z0-9_-]{11}' | head -n 1)"

    if [[ -n "$vid" ]]; then
        echo "$vid"
        return
    fi

    vid="$(run_cmd yt-dlp --no-warnings --get-id "$url")"
    echo "$vid"
}

# ---------------------------------------------
# Ambil master m3u8 tanpa cookies
# ---------------------------------------------
get_master_m3u8() {
    local url="$1"

    json=$(yt-dlp -J --no-warnings "$url" 2>/dev/null)

    # Ambil url format HLS pertama yang valid
    master=$(echo "$json" | jq -r '
        .formats[]
        | select(.protocol == "m3u8" or .url | test("m3u8"))
        | .url
    ' | head -n 1)

    echo "$master"
}

# ==============================
# MAIN
# ==============================
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
        echo "[!] Tidak bisa resolve ID: $url"
        continue
    fi

    resolved_url="https://www.youtube.com/watch?v=$video_id"

    m3u8=$(get_master_m3u8 "$resolved_url")

    if [[ -z "$m3u8" ]]; then
        echo "[!] Gagal dapat M3U8: $resolved_url"
        continue
    fi

    outfile="$WORKDIR/${safe}.m3u8.txt"

    echo "$m3u8" > "$outfile"

    echo "[✓] Disimpan: $outfile"

done < "$URL_FILE"
