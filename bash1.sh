#!/usr/bin/env bash

REPO_NAME="RENYAHKU"
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"
COOKIES_FILE="$HOME/cookies2.txt"
URL_FILE="$HOME/urls.txt"
OUTPUT_DIR="$(pwd)"

# Fungsi log: hanya tampilkan ke terminal, tidak disimpan ke file
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

if [ ! -f "$URL_FILE" ]; then
  log "[!] File $URL_FILE tidak ditemukan"
  exit 1
fi

while IFS=" " read -r name url; do
  [[ -z "$name" || "$name" == \#* ]] && continue
  safe_name=$(echo "$name" | tr -cd '[:alnum:]_.-')
  log "[*] Memproses: $name"

  if [[ "$url" == *"playlist?list="* ]]; then
    yt-dlp --no-warnings --cookies "$COOKIES_FILE" -j --flat-playlist \
      --extractor-args "youtube:player_client=web" \
      --user-agent "$USER_AGENT" "$url" |
    jq -r '.id' | while read -r vid; do
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
