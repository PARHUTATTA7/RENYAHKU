#!/usr/bin/env bash

REPO_NAME="RENYAHKU"
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"
COOKIES_FILE="$HOME/cookies.txt"
OUTPUT_DIR="${OUTPUT_DIR:-$(pwd)}"
URL_FILE="$HOME/urls.txt"
LOG_FILE="$OUTPUT_DIR/yt-download.log"

# Bersihkan log, hanya simpan hari ini dan kemarin
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

  if [[ "$url" == *"playlist?list="* ]]; then
    yt-dlp --cookies "$COOKIES_FILE" -j --flat-playlist --extractor-args "youtube:player_client=web" --user-agent "$USER_AGENT" "$url" |
    jq -r '.id' | while read -r vid; do
      direct_url=$(yt-dlp --cookies "$COOKIES_FILE" -g -f 18 --user-agent "$USER_AGENT" "https://www.youtube.com/watch?v=$vid")
      if [ -z "$direct_url" ]; then
        log "[!] Gagal ambil video dari playlist ($vid)"
        continue
      fi
      echo "$direct_url" > "$OUTPUT_DIR/${safe_name}_$vid.txt"
      log "[✓] URL dari playlist ($vid) disimpan: ${safe_name}_$vid.txt"
    done
  elif [[ "$url" == *.m3u8 ]]; then
    echo "$url" > "$OUTPUT_DIR/${safe_name}.m3u8.txt"
    log "[✓] M3U8 URL disimpan: ${safe_name}.m3u8.txt"
  else
    merged_url=$(yt-dlp --cookies "$COOKIES_FILE" -g -f 18 --user-agent "$USER_AGENT" "$url")
    if [ -z "$merged_url" ]; then
      log "[!] Gagal ambil URL (itag=18) untuk: $url"
      continue
    fi
    echo "$merged_url" > "$OUTPUT_DIR/${safe_name}.txt"
    log "[✓] URL (itag=18) disimpan: ${safe_name}.txt"
  fi
done < "$URL_FILE"

cd "$OUTPUT_DIR"
git config user.email "actions@github.com"
git config user.name "GitHub Actions"

git add .
git commit -m "Update dari ${REPO_NAME}/bash1.sh - $(date '+%Y-%m-%d %H:%M:%S')" || echo "[i] Tidak ada perubahan untuk commit"

# Pastikan tidak ada perubahan luar yang mengganggu
git stash push --include-untracked --message "temp-stash" || true
git pull --rebase origin master
git stash pop || true

git push origin master || {
  echo "[!] Push gagal, coba ulang setelah rebase"
  git pull --rebase origin master
  git push origin master || echo "[x] Gagal push setelah retry"
}
