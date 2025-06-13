#!/usr/bin/env bash

REPO_NAME="RENYAHKU"
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"
COOKIES_FILE="$HOME/cookies2.txt"
URL_FILE="$HOME/urls.txt"
OUTPUT_DIR="$(pwd)"
LOG_FILE="$OUTPUT_DIR/yt-download.log"

mkdir -p "$OUTPUT_DIR"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Bersihkan log, hanya simpan hari ini & kemarin
if [ -f "$LOG_FILE" ]; then
  grep -E "^\[($(date '+%Y-%m-%d')|$(date -d "yesterday" '+%Y-%m-%d'))" "$LOG_FILE" > "${LOG_FILE}.tmp"
  mv "${LOG_FILE}.tmp" "$LOG_FILE"
fi

# Cek file URL
if [ ! -f "$URL_FILE" ]; then
  log "[!] File $URL_FILE tidak ditemukan"
  exit 1
fi

while IFS=" " read -r name url; do
  [[ -z "$name" || "$name" == \#* ]] && continue
  safe_name=$(echo "$name" | tr -cd '[:alnum:]_.-')
  log "[*] Memproses: $name"

  if [[ "$url" == *"playlist?list="* ]]; then
    yt-dlp --cookies "$COOKIES_FILE" -j --flat-playlist --extractor-args "youtube:player_client=web" --user-agent "$USER_AGENT" "$url" |
    jq -r '.id' | while read -r vid; do
      direct_url=$(yt-dlp --cookies "$COOKIES_FILE" -g -f 18 --user-agent "$USER_AGENT" "https://www.youtube.com/watch?v=$vid")
      if [ -n "$direct_url" ]; then
        echo "$direct_url" > "$OUTPUT_DIR/${safe_name}_$vid.txt"
        log "[✓] URL dari playlist ($vid) disimpan: ${safe_name}_$vid.txt"
      else
        log "[!] Gagal ambil video dari playlist ($vid)"
      fi
    done
  elif [[ "$url" == *.m3u8 ]]; then
    log "[i] Lewatkan M3U8: $url"
  else
    direct_url=$(yt-dlp --cookies "$COOKIES_FILE" -g -f 18 --user-agent "$USER_AGENT" "$url")
    if [ -n "$direct_url" ]; then
      echo "$direct_url" > "$OUTPUT_DIR/${safe_name}.txt"
      log "[✓] URL (itag=18) disimpan: ${safe_name}.txt"
    else
      log "[!] Gagal ambil URL (itag=18) untuk: $url"
    fi
  fi
done < "$URL_FILE"

# Git commit & push
cd "$OUTPUT_DIR" || exit 1
git config user.email "actions@github.com"
git config user.name "GitHub Actions"

git add '*.txt' || { log "[!] Gagal git add"; exit 1; }

if git diff --cached --quiet; then
  log "[i] Tidak ada perubahan untuk commit"
else
  git commit -m "Update dari ${REPO_NAME}/bash1.sh - $(date '+%Y-%m-%d %H:%M:%S')" || { log "[!] Gagal commit"; exit 1; }
  git pull --rebase origin master || { log "[!] Gagal rebase"; exit 1; }
  git push origin master || { log "[!] Gagal push ke remote"; exit 1; }
fi
