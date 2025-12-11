#!/usr/bin/env bash

REPO_NAME="RENYAHKU"
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"
COOKIES_FILE="$HOME/cookies.txt"
URL_FILE="$HOME/urls_live.txt"
WORKDIR="$(pwd)"

# Fungsi untuk menjalankan command dengan suppression error
run_cmd() {
    "$@" 2>/dev/null
}

# Fungsi untuk fetch HTML
fetch_html() {
    curl -A "$USER_AGENT" -L -s --cookie "$COOKIES_FILE" "$1"
}

# Fungsi untuk membuat nama file yang aman
safe_filename() {
    echo "$1" | tr -cd '[:alnum:]_.-'
}

# Fungsi untuk mendapatkan video ID dari URL
get_video_id() {
    local url="$1"
    
    # 1. Ambil canonical link dari HTML
    html="$(fetch_html "$url")"
    vid="$(echo "$html" | grep -oP 'canonical" href="https://www.youtube.com/watch\?v=\K[A-Za-z0-9_-]{11}')"
    
    if [[ -n "$vid" ]]; then
        echo "$vid"
        return 0
    fi
    
    # 2. Ambil ID via yt-dlp
    vid="$(run_cmd yt-dlp --no-warnings --cookies "$COOKIES_FILE" --user-agent "$USER_AGENT" --get-id "$url")"
    
    if [[ -n "$vid" ]]; then
        echo "$vid"
        return 0
    fi
    
    # 3. Jika URL @username/live → search live video
    if [[ "$url" =~ youtube\.com/@([^/]+) ]]; then
        username="${BASH_REMATCH[1]}"
        data="$(run_cmd yt-dlp --no-warnings --cookies "$COOKIES_FILE" --user-agent "$USER_AGENT" --dump-single-json "ytsearch5:${username} live")"
        vid="$(echo "$data" | grep -oP '"id":\s*"\K[A-Za-z0-9_-]{11}' | head -n 1)"
        
        if [[ -n "$vid" ]]; then
            echo "$vid"
            return 0
        fi
    fi
    
    echo ""
    return 1
}

# Fungsi untuk mendapatkan master m3u8 dari JSON
get_master_m3u8() {
    local url="$1"
    local json master

    json="$(run_cmd yt-dlp \
        --no-warnings \
        --cookies "$COOKIES_FILE" \
        --user-agent "$USER_AGENT" \
        --dump-single-json \
        "$url")"

    # Jika JSON kosong → langsung FAIL
    if [[ -z "$json" || "$json" == "null" ]]; then
        echo ""
        return 1
    fi

    # Jika streamingData tidak ada → FAIL aman tanpa error jq
    if ! echo "$json" | jq -e '.streamingData.adaptiveFormats' >/dev/null 2>&1; then
        echo ""
        return 1
    fi

    # Ambil m3u8 tertinggi
    master="$(
        echo "$json" \
        | jq -r '
            .streamingData.adaptiveFormats
            | map(select(.url != null and (.url|test("m3u8"))))
            | sort_by(.height)
            | reverse
            | .[0].url // empty
        ' 2>/dev/null
    )"

    if [[ -n "$master" ]]; then
        echo "$master"
        return 0
    fi

    # Fallback kedua: url biasa tanpa filter tinggi
    master="$(echo "$json" | jq -r '.streamingData.adaptiveFormats[]?.url // empty' | grep '\.m3u8' | head -n 1)"

    if [[ -n "$master" ]]; then
        echo "$master"
        return 0
    fi

    echo ""
    return 1
}

### MAIN PROGRAM ###

# Cek apakah file URL ada
if [[ ! -f "$URL_FILE" ]]; then
    echo "[!] File $URL_FILE tidak ditemukan!"
    exit 1
fi

# Cek dependencies
if ! command -v yt-dlp &> /dev/null; then
    echo "[!] yt-dlp tidak ditemukan. Harap install terlebih dahulu."
    exit 1
fi

if ! command -v curl &> /dev/null; then
    echo "[!] curl tidak ditemukan. Harap install terlebih dahulu."
    exit 1
fi

# Proses setiap baris dalam file URL
while IFS= read -r line; do
    # Skip baris kosong atau komentar
    [[ -z "$line" ]] && continue
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    
    # Parse nama dan URL (menggunakan tab atau spasi sebagai delimiter)
    name=$(echo "$line" | awk '{print $1}')
    url=$(echo "$line" | sed 's/^[[:space:]]*[^[:space:]]*[[:space:]]*//')
    
    # Validasi
    if [[ -z "$name" || -z "$url" ]]; then
        echo "[!] Format tidak valid: $line"
        continue
    fi
    
    safe=$(safe_filename "$name")
    echo "[*] Memproses: $name"
    
    # Dapatkan video ID
    video_id=$(get_video_id "$url")
    
    if [[ -z "$video_id" ]]; then
        echo "[!] Tidak bisa resolve video ID untuk: $url"
        continue
    fi
    
    resolved_url="https://www.youtube.com/watch?v=$video_id"
    echo "[+] Resolved URL: $resolved_url"
    
    # Dapatkan master m3u8
    m3u8=$(get_master_m3u8 "$resolved_url")
    
    if [[ -z "$m3u8" ]]; then
        echo "[!] Gagal ambil master HLS untuk: $resolved_url"
        continue
    fi
    
    # Simpan ke file
    output_file="$WORKDIR/${safe}.m3u8.txt"
    echo "$m3u8" > "$output_file"
    
    if [[ -f "$output_file" ]]; then
        echo "[✓] Disimpan: $output_file"
    else
        echo "[!] Gagal menyimpan file: $output_file"
    fi
    
done < "$URL_FILE"

### GIT OPERATIONS ###

# Konfigurasi git
git config user.email "actions@github.com"
git config user.name "GitHub Actions"

# Commit jika ada perubahan
git add .

if ! git diff --cached --quiet; then
    commit_msg="Update dari $REPO_NAME/bash2.sh - $(date '+%Y-%m-%d %H:%M:%S')"
    git commit -m "$commit_msg"
    
    # Sync dengan remote
    git fetch origin master
    
    # Gunakan strategy yang lebih aman
    if git merge --strategy-option=theirs origin/master 2>/dev/null; then
        git push origin master
        echo "[✓] Berhasil push ke repository"
    else
        echo "[!] Gagal merge dengan remote"
        # Fallback: force push jika diperlukan
        git push --force-with-lease origin master
    fi
else
    echo "[i] Tidak ada perubahan yang perlu di-commit"
fi

echo "[✓] Script selesai"
