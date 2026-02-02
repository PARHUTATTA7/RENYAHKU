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

# ================= GET LIVE STREAM URL (SOLUSI BARU) =================

get_live_stream_url() {
    local url="$1"
    local stream_url
    
    # SOLUSI: Gunakan player_client=android seperti contoh Anda
    # Ini memaksa yt-dlp menggunakan client Android yang lebih mudah mendapatkan HLS
    
    echo "[*] Mencoba dengan player_client=android..."
    stream_url="$(run_cmd yt-dlp \
        --no-warnings \
        --cookies "$COOKIES_FILE" \
        --user-agent "$USER_AGENT" \
        --extractor-args "youtube:player_client=android" \
        -f "best[height<=720]" \
        -g "$url" 2>/dev/null | head -n 1)"
    
    [[ -n "$stream_url" && "$stream_url" == *".m3u8"* ]] && { 
        echo "[+] Berhasil dengan player_client=android"
        echo "$stream_url"
        return 0
    }
    
    # Fallback 1: Coba dengan tambahan parameter live
    echo "[*] Mencoba dengan live-from-start..."
    stream_url="$(run_cmd yt-dlp \
        --no-warnings \
        --cookies "$COOKIES_FILE" \
        --user-agent "$USER_AGENT" \
        --live-from-start \
        --extractor-args "youtube:player_client=android" \
        -f "best" \
        -g "$url" 2>/dev/null | head -n 1)"
    
    [[ -n "$stream_url" ]] && { 
        echo "[+] Berhasil dengan live-from-start"
        echo "$stream_url"
        return 0
    }
    
    # Fallback 2: Coba format khusus live
    echo "[*] Mencoba format live khusus..."
    stream_url="$(run_cmd yt-dlp \
        --no-warnings \
        --cookies "$COOKIES_FILE" \
        --user-agent "$USER_AGENT" \
        --extractor-args "youtube:player_client=android" \
        -f "bestvideo[height<=720]+bestaudio/best[height<=720]" \
        -g "$url" 2>/dev/null | head -n 1)"
    
    echo "$stream_url"
}

# ================= SIMPLE LIVE CHECK =================

quick_live_check() {
    local url="$1"
    
    # Cepat cek apakah ada format live (91-96) atau kata live
    local formats
    formats="$(run_cmd yt-dlp --no-warnings --cookies "$COOKIES_FILE" \
        --user-agent "$USER_AGENT" --list-formats "$url" 2>/dev/null)"
    
    if echo "$formats" | grep -q "91\|92\|93\|94\|95\|96\|live"; then
        return 0
    fi
    
    # Cek di HTML
    local html
    html="$(fetch_html "$url" | head -1000)"
    if echo "$html" | grep -qi "live\|broadcast"; then
        return 0
    fi
    
    return 1
}

# ================= MAIN =================

[[ ! -f "$URL_FILE" ]] && { echo "[!] File $URL_FILE tidak ditemukan"; exit 1; }
command -v yt-dlp >/dev/null || { echo "[!] yt-dlp tidak ditemukan"; exit 1; }
command -v curl >/dev/null || { echo "[!] curl tidak ditemukan"; exit 1; }

# Counter untuk statistik
success_count=0
fail_count=0

while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    [[ "$line" =~ ^[[:space:]]*# ]] && continue

    name="$(echo "$line" | awk '{print $1}')"
    url="$(echo "$line" | sed 's/^[[:space:]]*[^[:space:]]*[[:space:]]*//')"

    [[ -z "$name" || -z "$url" ]] && { 
        echo "[!] Format tidak valid: $line"
        ((fail_count++))
        continue
    }

    safe="$(safe_filename "$name")"
    echo ""
    echo "========================================"
    echo "[*] Memproses: $name"
    echo "[*] URL: $url"

    # Dapatkan video ID atau gunakan URL langsung
    video_id="$(get_video_id "$url")"
    if [[ -n "$video_id" ]]; then
        resolved_url="https://www.youtube.com/watch?v=$video_id"
        echo "[+] Video ID: $video_id"
    else
        resolved_url="$url"
        echo "[+] Menggunakan URL langsung"
    fi
    
    echo "[+] Target URL: $resolved_url"
    
    # Quick check (optional)
    if quick_live_check "$resolved_url"; then
        echo "[+] Terdeteksi sebagai live stream"
    else
        echo "[*] Tidak terdeteksi live, tetap lanjut..."
    fi
    
    # Ambil stream URL dengan metode baru
    echo "[*] Mengambil stream URL..."
    stream_url="$(get_live_stream_url "$resolved_url")"
    
    # Validasi hasil
    if [[ -z "$stream_url" || "$stream_url" == "null" || "$stream_url" == "NA" ]]; then
        echo "[!] GAGAL: Tidak dapat stream URL"
        echo "[*] Debug - Testing manual command:"
        echo "     yt-dlp -g --extractor-args \"youtube:player_client=android\" \"$resolved_url\""
        
        # Coba langsung command yang Anda berikan
        temp_result="$(run_cmd yt-dlp -4 -g --extractor-args "youtube:player_client=android" "$resolved_url")"
        if [[ -n "$temp_result" ]]; then
            echo "[!] TAPI berhasil dengan command langsung!"
            stream_url="$temp_result"
        else
            ((fail_count++))
            continue
        fi
    fi
    
    # Pastikan URL valid
    if [[ "$stream_url" != http* ]]; then
        echo "[!] ERROR: URL tidak valid: $stream_url"
        ((fail_count++))
        continue
    fi
    
    # Cek apakah URL mengandung m3u8 (optional)
    if [[ "$stream_url" == *".m3u8"* ]]; then
        echo "[✓] URL mengandung m3u8 (HLS)"
    fi
    
    # Tampilkan preview URL
    echo "[✓] SUKSES: Dapat stream URL"
    echo "[*] Preview URL: ${stream_url:0:100}..."
    
    # Simpan ke file
    output_file="$WORKDIR/${safe}.txt"
    echo "$stream_url" > "$output_file"
    echo "[✓] Disimpan ke: $output_file"
    
    ((success_count++))
    
    # Beri jeda singkat antara proses
    sleep 1

done < "$URL_FILE"

# ================= SUMMARY =================
echo ""
echo "========================================"
echo "           HASIL PROSES"
echo "========================================"
echo "[✓] Berhasil: $success_count"
echo "[!] Gagal: $fail_count"
echo "========================================"

# ================= GIT =================

if [[ $success_count -gt 0 ]]; then
    git config user.email "actions@github.com"
    git config user.name "GitHub Actions"

    git add .

    if ! git diff --cached --quiet; then
        git commit -m "Update stream URLs - $(date '+%Y-%m-%d %H:%M:%S') - Success: $success_count"
        git fetch origin master
        git merge --strategy-option=theirs origin/master 2>/dev/null || true
        git push origin master --force-with-lease
        echo "[✓] Berhasil push ke repository"
    else
        echo "[i] Tidak ada perubahan"
    fi
fi

echo "[✓] Script selesai"
