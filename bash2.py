#!/usr/bin/env bash

USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
COOKIES_FILE="$HOME/cookies.txt"
URL_FILE="$HOME/urls_live.txt"

process() {
    name="$1"
    url="$2"
    safe=$(echo "$name" | tr -cd '[:alnum:]_.-')

    echo "[*] Memproses: $name"

    m3u8=$(yt-dlp --no-warnings --cookies "$COOKIES_FILE" --user-agent "$USER_AGENT" \
                  --print "%(manifest_url)s" "$url" 2>/dev/null)

    if [[ "$m3u8" == http* && "$m3u8" == *m3u8* ]]; then
        echo "$m3u8" > "${safe}.m3u8.txt"
        echo "[✓] Tersimpan: ${safe}.m3u8.txt"
    else
        echo "[!] Gagal ambil manifest: $url"
    fi
}

export -f process
export USER_AGENT COOKIES_FILE

grep -v '^#' "$URL_FILE" \
| awk '{name=$1; $1=""; url=$0; sub(/^ /,"",url); print name "|" url}' \
| xargs -P 10 -I {} bash -c '
    IFS="|" read name url <<< "{}"
    process "$name" "$url"
'
