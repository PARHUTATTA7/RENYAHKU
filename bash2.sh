#!/usr/bin/env bash

REPO_NAME="RENYAHKU"
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"
COOKIES_FILE="$HOME/cookies.txt"
URL_FILE="$HOME/urls_live.txt"
API_FILE="$HOME/base_api.txt"
WORKDIR="$(pwd)"

# ================= UTIL =================

fetch_html() {
    curl -A "$USER_AGENT" -L -s --cookie "$COOKIES_FILE" "$1"
}

safe_filename() {
    echo "$1" | tr -cd '[:alnum:]_.-'
}

# ================= LOAD API BASE =================

load_api_base() {
    [[ ! -f "$API_FILE" ]] && { echo "[!] File API tidak ditemukan: $API_FILE"; exit 1; }

    API_BASE="$(head -n 1 "$API_FILE" | tr -d '\r\n')"

    [[ -z "$API_BASE" ]] && { echo "[!] API_BASE kosong di file: $API_FILE"; exit 1; }

    echo "[+] API_BASE loaded: $API_BASE"
}

# ================= VIDEO ID EXTRACTOR =================

get_video_id() {
    local url="$1"
    local html vid

    if [[ "$url" =~ v=([A-Za-z0-9_-]{11}) ]]; then echo "${BASH_REMATCH[1]}"; return 0; fi
    if [[ "$url" =~ youtu\.be/([A-Za-z0-9_-]{11}) ]]; then echo "${BASH_REMATCH[1]}"; return 0; fi
    if [[ "$url" =~ youtube\.com/live/([A-Za-z0-9_-]{11}) ]]; then echo "${BASH_REMATCH[1]}"; return 0; fi
    if [[ "$url" =~ youtube\.com/shorts/([A-Za-z0-9_-]{11}) ]]; then echo "${BASH_REMATCH[1]}"; return 0; fi
    if [[ "$url" =~ youtube\.com/embed/([A-Za-z0-9_-]{11}) ]]; then echo "${BASH_REMATCH[1]}"; return 0; fi

    html="$(fetch_html "$url")"

    vid="$(echo "$html" | grep -oP 'canonical" href="https://www\.youtube\.com/watch\?v=\K[A-Za-z0-9_-]{11}' | head -n 1)"
    [[ -n "$vid" ]] && { echo "$vid"; return 0; }

    vid="$(echo "$html" | grep -oP '"videoId":"\K[A-Za-z0-9_-]{11}' | head -n 1)"
    [[ -n "$vid" ]] && { echo "$vid"; return 0; }

    vid="$(echo "$html" | grep -oP 'watch\?v=\K[A-Za-z0-9_-]{11}' | head -n 1)"
    [[ -n "$vid" ]] && { echo "$vid"; return 0; }

    return 1
}

# ================= GENERATE MASTER M3U8 =================

generate_master_m3u8() {
    local name="$1"
    local content="$2"
    local output_file="$3"

    echo "#EXTM3U" > "$output_file"

    # Ambil semua URL + sort berdasarkan itag tertinggi
    echo "$content" \
        | grep -oE 'https://manifest\.googlevideo\.com[^[:space:]]+' \
        | awk -F'itag=' '{print $2 "|" $0}' \
        | sort -t'|' -k1 -nr \
        | cut -d'|' -f2 \
        | uniq \
        | while read -r url; do

        itag=$(echo "$url" | grep -o 'itag=[0-9]*' | cut -d= -f2)

        case "$itag" in
            96) res="1920x1080"; bw="5000000"; label="1080p";;
            95) res="1280x720";  bw="3000000"; label="720p";;
            94) res="854x480";   bw="1500000"; label="480p";;
            93) res="640x360";   bw="800000";  label="360p";;
            92) res="426x240";   bw="400000";  label="240p";;
            91) res="256x144";   bw="200000";  label="144p";;
            *) continue;;
        esac

        echo "#EXT-X-STREAM-INF:BANDWIDTH=$bw,RESOLUTION=$res,NAME=\"$label\"" >> "$output_file"
        echo "$url" >> "$output_file"

    done
}

# ================= MAIN =================

[[ ! -f "$URL_FILE" ]] && { echo "[!] File $URL_FILE tidak ditemukan"; exit 1; }
command -v curl >/dev/null || { echo "[!] curl tidak ditemukan"; exit 1; }

load_api_base

while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    [[ "$line" =~ ^[[:space:]]*# ]] && continue

    name="$(echo "$line" | awk '{print $1}')"
    url="$(echo "$line" | sed 's/^[[:space:]]*[^[:space:]]*[[:space:]]*//')"

    [[ -z "$name" || -z "$url" ]] && { echo "[!] Format tidak valid: $line"; continue; }

    safe="$(safe_filename "$name")"

    echo "[*] Memproses: $name"

    video_id="$(get_video_id "$url")"
    [[ -z "$video_id" ]] && { echo "[!] Gagal resolve video ID: $url"; continue; }

    echo "[+] Video ID: $video_id"

    api_response="$(curl -A "$USER_AGENT" -L -s "${API_BASE}${video_id}" | tr -d '\000' | tr -d '\r')"

    [[ -z "$api_response" ]] && { echo "[!] API kosong untuk ID: $video_id"; continue; }

    output_file="$WORKDIR/${safe}.m3u8"

    generate_master_m3u8 "$name" "$api_response" "$output_file"

    echo "[✓] Master M3U8 dibuat: $output_file"

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
