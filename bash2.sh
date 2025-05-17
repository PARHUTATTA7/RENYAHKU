#!/usr/bin/env bash

REPO_NAME="RENYAHKU"
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"
COOKIES_FILE="$HOME/cookies.txt"
OUTPUT_DIR="${OUTPUT_DIR:-$(pwd)}"
URL_FILE="$HOME/urls_live.txt"
LOG_FILE="$OUTPUT_DIR/yt-m3u8.log"

if [ -f "$LOG_FILE" ]; then
  tmp_log="${LOG_FILE}.tmp"
  today=$(date '+%Y-%m-%d')
  yesterday=$(date -d "yesterday" '+%Y-%m-%d')
  grep -E "^\[($today|$yesterday)" "$LOG_FILE" > "$tmp_log"
  mv "$tmp_log" "$LOG_FILE"
fi

mkdir -p "$OUTPUT_DIR"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

if [ ! -f "$URL_FILE" ]; then
  log "[!] File $URL_FILE tidak ditemukan"
  exit 1
fi

while IFS=" " read -r name url; do
  [[ -z "$name" || "$name" == \#* ]] && continue
  safe_name=$(echo "$name" | tr -cd '[:alnum:]_.-')
  log "[*] Memproses: $name"

  video_id=$(yt-dlp --cookies "$COOKIES_FILE" --get-id "$url" 2>/dev/null)
  if [ -z "$video_id" ]; then
    log "[!] Tidak bisa resolve video ID dari: $url"
    continue
  fi
  resolved_url="https://www.youtube.com/watch?v=$video_id"

  m3u8_url=$(yt-dlp --cookies "$COOKIES_FILE" --user-agent "$USER_AGENT" -g -f "best[ext=m3u8]" "$resolved_url" 2>/dev/null | grep -E '^https?://' | tail -n1)

  if [[ -z "$m3u8_url" ]]; then
    log "[!] Gagal ambil URL .m3u8 untuk: $resolved_url, coba fallback best format"
    m3u8_url=$(yt-dlp --cookies "$COOKIES_FILE" --user-agent "$USER_AGENT" -g -f "best" "$resolved_url" 2>/dev/null | grep -E '^https?://' | tail -n1)
  fi

  if [[ -z "$m3u8_url" ]]; then
    log "[!] Gagal ambil URL streaming untuk: $resolved_url"
    continue
  fi

  echo "$m3u8_url" > "$OUTPUT_DIR/${safe_name}.m3u8.txt"
  log "[✓] URL streaming disimpan: ${safe_name}.m3u8.txt"
done < "$URL_FILE"

cd "$OUTPUT_DIR"
git config user.email "actions@github.com"
git config user.name "GitHub Actions"

# Hanya add file yang ada di dalam folder ini saja
git add . || true

# Commit jika ada perubahan di folder output
if ! git diff --cached --quiet; then
  git commit -m "Update dari ${REPO_NAME}/bash2.sh - $(date '+%Y-%m-%d %H:%M:%S')"
else
  echo "[i] Tidak ada perubahan untuk commit"
fi

# Pull tanpa rebase jika tidak butuh sinkron master utama (karena hanya push data)
git fetch origin master
git merge --strategy=ours origin/master || true

# Push
git push origin master || echo "[x] Gagal push"
