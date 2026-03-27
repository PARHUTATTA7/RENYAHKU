#!/usr/bin/env bash

REPO_NAME="RENYAHKU"
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"
COOKIES_FILE="$HOME/cookies.txt"
URL_FILE="$HOME/urls_live.txt"
API_FILE="$HOME/base_api.txt"
WORKDIR="$(pwd)"
OUTPUT_FILE="$WORKDIR/result.txt"  # File untuk menyimpan semua URL

# ================= UTIL =================
fetch_html() {
    curl -A "$USER_AGENT" -L -s --cookie "$COOKIES_FILE" "$1"
}

# ================= LOAD API BASE =================
load_api_base() {
    [[ ! -f "$API_FILE" ]] && { echo "[!] File API tidak ditemukan: $API_FILE"; exit 1; }
    API_BASE="$(head -n 1 "$API_FILE" | tr -d '\r\n')"
    [[ -z "$API_BASE" ]] && { echo "[!] API_BASE kosong di file: $API_FILE"; exit 1; }
    echo "[+] API_BASE loaded"
}

# ================= VIDEO ID EXTRACTOR =================
get_video_id() {
    local url="$1"
    local html vid
    
    # 1) watch?v=
    if [[ "$url" =~ v=([A-Za-z0-9_-]{11}) ]]; then
        echo "${BASH_REMATCH[1]}"
        return 0
    fi
    
    # 2) youtu.be/ID
    if [[ "$url" =~ youtu\.be/([A-Za-z0-9_-]{11}) ]]; then
        echo "${BASH_REMATCH[1]}"
        return 0
    fi
    
    # 3) /live/ID
    if [[ "$url" =~ youtube\.com/live/([A-Za-z0-9_-]{11}) ]]; then
        echo "${BASH_REMATCH[1]}"
        return 0
    fi
    
    # 4) /shorts/ID
    if [[ "$url" =~ youtube\.com/shorts/([A-Za-z0-9_-]{11}) ]]; then
        echo "${BASH_REMATCH[1]}"
        return 0
    fi
    
    # 5) /embed/ID
    if [[ "$url" =~ youtube\.com/embed/([A-Za-z0-9_-]{11}) ]]; then
        echo "${BASH_REMATCH[1]}"
        return 0
    fi
    
    # 6) kalau @username/live atau URL aneh, parse HTML nya
    html="$(fetch_html "$url")"
    
    # cari dari canonical
    vid="$(echo "$html" | grep -oP 'canonical" href="https://www\.youtube\.com/watch\?v=\K[A-Za-z0-9_-]{11}' | head -n 1)"
    [[ -n "$vid" ]] && { echo "$vid"; return 0; }
    
    # cari dari "videoId":"ID"
    vid="$(echo "$html" | grep -oP '"videoId":"\K[A-Za-z0-9_-]{11}' | head -n 1)"
    [[ -n "$vid" ]] && { echo "$vid"; return 0; }
    
    # cari dari watch?v=ID di html
    vid="$(echo "$html" | grep -oP 'watch\?v=\K[A-Za-z0-9_-]{11}' | head -n 1)"
    [[ -n "$vid" ]] && { echo "$vid"; return 0; }
    
    return 1
}

# ================= GET M3U8 FROM API =================
get_m3u8_from_api() {
    local video_id="$1"
    local api_url="${API_BASE}${video_id}"
    local response
    
    response=$(curl -A "$USER_AGENT" -L -s "$api_url" | tr -d '\000' | tr -d '\r')
    
    # Ambil URL m3u8 langsung
    echo "$response" | grep -oE 'https?://[^"]+\.m3u8[^"]*' | head -n 1
}

# ================= MAIN =================
main() {
    [[ ! -f "$URL_FILE" ]] && { echo "[!] File $URL_FILE tidak ditemukan"; exit 1; }
    command -v curl >/dev/null || { echo "[!] curl tidak ditemukan"; exit 1; }
    
    load_api_base
    
    # Kosongkan file output
    > "$OUTPUT_FILE"
    
    local total_urls=0
    local success_urls=0
    
    while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        [[ "$line" =~ ^[[:space:]]*# ]] && continue
        
        name="$(echo "$line" | awk '{print $1}')"
        url="$(echo "$line" | sed 's/^[[:space:]]*[^[:space:]]*[[:space:]]*//')"
        
        [[ -z "$name" || -z "$url" ]] && { echo "[!] Format tidak valid: $line"; continue; }
        
        total_urls=$((total_urls + 1))
        echo "[*] Memproses: $name"
        
        video_id="$(get_video_id "$url")"
        [[ -z "$video_id" ]] && { echo "[!] Gagal resolve video ID: $url"; continue; }
        
        echo "[+] Video ID: $video_id"
        
        m3u8="$(get_m3u8_from_api "$video_id")"
        [[ -z "$m3u8" ]] && { echo "[!] API gagal kasih m3u8 untuk ID: $video_id"; continue; }
        
        # Tampilkan URL ke terminal
        echo "[✓] M3U8 URL: $m3u8"
        
        # Simpan URL ke file output
        echo "$m3u8" >> "$OUTPUT_FILE"
        
        success_urls=$((success_urls + 1))
        echo "---"
        
    done < "$URL_FILE"
    
    echo ""
    echo "======================= SUMMARY ======================="
    echo "Total URL diproses: $total_urls"
    echo "Berhasil: $success_urls"
    echo "Gagal: $((total_urls - success_urls))"
    echo "Semua URL tersimpan di: $OUTPUT_FILE"
    echo "======================================================="
    
    # Tampilkan semua URL yang berhasil
    if [[ $success_urls -gt 0 ]]; then
        echo ""
        echo "Daftar URL M3U8 yang berhasil didapat:"
        cat "$OUTPUT_FILE"
    fi
}

# ================= GIT =================
git_push() {
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
}

# Jalankan main function
main

# Push ke git jika diperlukan (komentar jika tidak ingin push)
# git_push

echo "[✓] Script selesai"
