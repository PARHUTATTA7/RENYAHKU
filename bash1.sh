#!/usr/bin/env bash

REPO_NAME="RENYAHKU"
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36"
COOKIES_FILE="$HOME/cookies2.txt"
URL_FILE="$HOME/urls.txt"
OUTPUT_DIR="$(pwd)"
LOG_FILE="$OUTPUT_DIR/yt-download.log"

# Bersihkan log, hanya simpan hari ini dan kemarin
mkdir -p "$OUTPUT_DIR"
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
      output_file="${safe_name}_$vid.txt"
      tmp_file="${output_file}.tmp"
      {
        echo "$direct_url"
        echo "# Generated: $(date '+%Y-%m-%d %H:%M:%S')"
      } > "$tmp_file"

      if ! cmp -s "$tmp_file" "$output_file"; then
        mv "$tmp_file" "$output_file"
        log "[✓] Diupdate: $output_file"
      else
        rm "$tmp_file"
        log "[=] Tidak berubah: $output_file"
      fi
    done
  elif [[ "$url" == *.m3u8 ]]; then
    log "[i] Lewatkan M3U8: $url"
  else
    merged_url=$(yt-dlp --cookies "$COOKIES_FILE" -g -f 18 --user-agent "$USER_AGENT" "$url")
    if [ -z "$merged_url" ]; then
      log "[!] Gagal ambil URL (itag=18) untuk: $url"
      continue
    fi

    output_file="${safe_name}.txt"
    tmp_file="${output_file}.tmp"
    {
      echo "$merged_url"
      echo "# Generated: $(date '+%Y-%m-%d %H:%M:%S')"
    } > "$tmp_file"

    if ! cmp -s "$tmp_file" "$output_file"; then
      mv "$tmp_file" "$output_file"
      log "[✓] Diupdate: $output_file"
    else
      rm "$tmp_file"
      log "[=] Tidak berubah: $output_file"
    fi
  fi
done < "$URL_FILE"
