#!/usr/bin/env bash
REPO_NAME="RENYAHKU"
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
COOKIES_FILE="$HOME/cookies.txt"
URL_FILE="$HOME/urls_live.txt"
WORKDIR="$(pwd)"

resolve_id() {
    yt-dlp --no-warnings --cookies "$COOKIES_FILE" --user-agent "$USER_AGENT" \
           --get-id "$1" 2>/dev/null
}

get_manifest() {
    yt-dlp --no-warnings --cookies "$COOKIES_FILE" --user-agent "$USER_AGENT" \
           --print "%(manifest_url)s" "$1" 2>/dev/null
}

process() {
    name="$1"
    url="$2"
    safe=$(echo "$name" | tr -cd '[:alnum:]_.-')

    echo "[*] Memproses: $name"

    # 1. resolve video ID
    vid=$(resolve_id "$url")

    if [[ -z "$vid" ]]; then
        echo "[!] Tidak menemukan live video: $url"
        return
    fi

    full_url="https://www.youtube.com/watch?v=$vid"

    # 2. ambil manifest HLS
    m3u8=$(get_manifest "$full_url")

    if [[ "$m3u8" == http* && "$m3u8" == *m3u8* ]]; then
        echo "$m3u8" > "${safe}.m3u8.txt"
        echo "[✓] Tersimpan: ${safe}.m3u8.txt"
    else
        echo "[!] Manifest gagal untuk ID: $vid"
    fi
}

export -f process resolve_id get_manifest
export USER_AGENT COOKIES_FILE

grep -v '^#' "$URL_FILE" \
| awk '{name=$1; $1=""; url=$0; sub(/^ /,"",url); print name "|" url}' \
| xargs -P 10 -I {} bash -c '
    IFS="|" read name url <<< "{}"
    process "$name" "$url"
'
