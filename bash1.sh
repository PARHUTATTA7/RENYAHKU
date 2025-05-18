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
    log "[i] Lewatkan M3U8: $url"
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

cd "$OUTPUT_DIR" || exit 1
git config user.email "actions@github.com"
git config user.name "GitHub Actions"

# Hanya add file yang ada di dalam folder ini saja
git add . || { log "[!] Gagal menambahkan file ke git"; exit 1; }

# Commit jika ada perubahan di folder output
if ! git diff --cached --quiet; then
  git commit -m "Update dari ${REPO_NAME}/bash1.sh - $(date '+%Y-%m-%d %H:%M:%S')" || { log "[!] Gagal melakukan commit"; exit 1; }
else
  log "[i] Tidak ada perubahan untuk commit"
fi

# Pull tanpa rebase jika tidak butuh sinkron master utama (karena hanya push data)
git fetch origin master
git merge --strategy=ours origin/master || { log "[!] Gagal melakukan merge"; exit 1; }

# Push
git push origin master || { log "[!] Gagal push ke remote"; exit 1; }
