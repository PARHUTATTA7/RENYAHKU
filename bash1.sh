#!/usr/bin/env bash

REPO_NAME="RENYAHKU"
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"
COOKIES_FILE="$HOME/cookies2.txt"
URL_FILE="$HOME/urls.txt"
OUTPUT_DIR="$(pwd)"

# Default delay (detik)
MIN_DELAY=5
MAX_DELAY=15
NO_DELAY=false

# Parsing argumen
while [[ $# -gt 0 ]]; do
  case "$1" in
    --min-delay)
      MIN_DELAY="$2"
      shift 2
      ;;
    --max-delay)
      MAX_DELAY="$2"
      shift 2
      ;;
    --no-delay)
      NO_DELAY=true
      shift
      ;;
    *)
      echo "Argumen tidak dikenal: $1"
      echo "Usage: $0 [--min-delay N] [--max-delay M] [--no-delay]"
      exit 1
      ;;
  esac
done

# Fungsi log
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

if [ ! -f "$URL_FILE" ]; then
  log "[!] File $URL_FILE tidak ditemukan"
  exit 1
fi

# fungsi sleep random biar gak ke-limit
sleep_random() {
  if [ "$NO_DELAY" = true ]; then
    log "[~] Mode no-delay aktif, skip sleep"
    return
  fi

  if [ "$MAX_DELAY" -lt "$MIN_DELAY" ]; then
    log "[!] max-delay ($MAX_DELAY) lebih kecil dari min-delay ($MIN_DELAY), gunakan default 5–15"
    MIN_DELAY=5
    MAX_DELAY=15
  fi
  delay=$(( (RANDOM % (MAX_DELAY - MIN_DELAY + 1)) + MIN_DELAY ))
  log "[~] Tidur $delay detik untuk hindari rate-limit"
  sleep $delay
}

while IFS=" " read -r name url; do
  [[ -z "$name" || "$name" == \#* ]] && continue
  safe_name=$(echo "$name" | tr -cd '[:alnum:]_.-')
  log "[*] Memproses: $name"

  if [[ "$url" == *"playlist?list="* ]]; then
    yt-dlp --no-warnings --cookies "$COOKIES_FILE" -j --flat-playlist \
      --extractor-args "youtube:player_client=web" \
      --user-agent "$USER_AGENT" "$url" |
    jq -r '.id' | while read -r vid; do
      sleep_random
      direct_url=$(yt-dlp --no-warnings --cookies "$COOKIES_FILE" -g -f 18 \
        --user-agent "$USER_AGENT" "https://www.youtube.com/watch?v=$vid")
      if [ -z "$direct_url" ]; then
        log "[!] Gagal ambil video dari playlist ($vid)"
        continue
      fi
      echo "$direct_url" > "$OUTPUT_DIR/${safe_name}_$vid.txt"
      log "[✓] URL dari playlist ($vid) disimpan: ${safe_name}_$vid.txt"
    done
  elif [[ "$url" == *.m3u8 ]]; then
    log "[i] Lewatkan M3U8: $url"
  else
    sleep_random
    merged_url=$(yt-dlp --no-warnings --cookies "$COOKIES_FILE" -g -f 18 \
      --user-agent "$USER_AGENT" "$url")
    if [ -z "$merged_url" ]; then
      log "[!] Gagal ambil URL (itag=18) untuk: $url"
      continue
    fi
    echo "$merged_url" > "$OUTPUT_DIR/${safe_name}.txt"
    log "[✓] URL (itag=18) disimpan: ${safe_name}.txt"
  fi
done < "$URL_FILE"
