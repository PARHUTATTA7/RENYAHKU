#!/usr/bin/env bash

REPO_NAME="RENYAHKU"
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"
COOKIES_FILE="$HOME/cookies2.txt"
URL_FILE="$HOME/urls.txt"
OUTPUT_DIR="$(pwd)"
LOG_FILE="$OUTPUT_DIR/yt-download.log"
PROXY_LIST_URL_FILE="$HOME/proxylisturl.txt"

mkdir -p "$OUTPUT_DIR"

# 🧹 Bersihkan log, hanya simpan hari ini dan kemarin
if [ -f "$LOG_FILE" ]; then
  tmp_log="${LOG_FILE}.tmp"
  today=$(date '+%Y-%m-%d')
  yesterday=$(date -d "yesterday" '+%Y-%m-%d')
  grep -E "^\[($today|$yesterday)" "$LOG_FILE" > "$tmp_log"
  mv "$tmp_log" "$LOG_FILE"
fi

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

if [ ! -f "$URL_FILE" ]; then
  log "[!] File $URL_FILE tidak ditemukan"
  exit 1
fi

if [ ! -f "$PROXY_LIST_URL_FILE" ]; then
  log "[!] File $PROXY_LIST_URL_FILE tidak ditemukan"
  exit 1
fi

# 🚀 Ambil daftar proxy dari URL dalam file
PROXY_SOURCE_URL=$(head -n 1 "$PROXY_LIST_URL_FILE")
log "[*] Mengambil daftar proxy dari: $PROXY_SOURCE_URL"

PROXY=$(curl -fsSL "$PROXY_SOURCE_URL" | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+:[0-9]+$' | shuf -n1)

if [[ -z "$PROXY" ]]; then
  log "[!] Gagal mendapatkan proxy dari $PROXY_SOURCE_URL"
  exit 1
fi

log "[✓] Menggunakan proxy: $PROXY"

# 📦 Mulai proses setiap URL
while IFS=" " read -r name url; do
  [[ -z "$name" || "$name" == \#* ]] && continue
  safe_name=$(echo "$name" | tr -cd '[:alnum:]_.-')
  log "[*] Memproses: $name"

  if [[ "$url" == *"playlist?list="* ]]; then
    yt-dlp --proxy "http://$PROXY" --cookies "$COOKIES_FILE" -j --flat-playlist --extractor-args "youtube:player_client=web" --user-agent "$USER_AGENT" "$url" |
    jq -r '.id' | while read -r vid; do
      direct_url=$(yt-dlp --proxy "http://$PROXY" --cookies "$COOKIES_FILE" -g -f 18 --user-agent "$USER_AGENT" "https://www.youtube.com/watch?v=$vid")
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
    merged_url=$(yt-dlp --proxy "http://$PROXY" --cookies "$COOKIES_FILE" -g -f 18 --user-agent "$USER_AGENT" "$url")
    if [ -z "$merged_url" ]; then
      log "[!] Gagal ambil URL (itag=18) untuk: $url"
      continue
    fi
    echo "$merged_url" > "$OUTPUT_DIR/${safe_name}.txt"
    log "[✓] URL (itag=18) disimpan: ${safe_name}.txt"
  fi
done < "$URL_FILE"
