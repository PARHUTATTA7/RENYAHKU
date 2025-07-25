import subprocess
from pathlib import Path

# Lokasi file channel
CHANNEL_FILE = Path.home() / "channel.txt"

def get_twitch_m3u8_url(channel_name):
    try:
        result = subprocess.run(
            ['streamlink', f'https://twitch.tv/{channel_name}', 'best', '--stream-url'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Gagal mendapatkan URL M3U8 untuk {channel_name}: {e.stderr.strip()}")
        return None

def main():
    if not CHANNEL_FILE.exists():
        print(f"❌ File tidak ditemukan: {CHANNEL_FILE}")
        return

    with open(CHANNEL_FILE, "r") as f:
        channels = [line.strip() for line in f if line.strip()]

    for channel in channels:
        print(f"🔄 Memproses channel: {channel}")
        m3u8_url = get_twitch_m3u8_url(channel)
        if m3u8_url:
            try:
                output_file = Path(f"{channel}.txt")
                with open(output_file, "w") as f_out:
                    f_out.write(m3u8_url + "\n")
                print(f"✅ Disimpan ke {output_file}")
            except Exception as e:
                print(f"❌ Gagal menulis file {channel}.txt: {e}")
        else:
            print(f"⚠️ Tidak ada URL untuk {channel}")

if __name__ == "__main__":
    main()
