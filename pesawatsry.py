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
        output_file = Path(f"{channel}.m3u8.txt")

        if m3u8_url:
            try:
                with open(output_file, "w") as f_out:
                    f_out.write(m3u8_url + "\n")
                print(f"✅ Disimpan ke {output_file}")
            except Exception as e:
                print(f"❌ Gagal menulis file {channel}.m3u8.txt: {e}")
        else:
            # Buat file kosong untuk memastikan fallback bisa bekerja
            try:
                output_file.touch(exist_ok=True)
                # Pastikan benar-benar kosong
                open(output_file, "w").close()
                print(f"⚠️ Tidak ada URL untuk {channel} → File kosong dibuat: {output_file}")
            except Exception as e:
                print(f"❌ Gagal membuat file kosong {channel}.m3u8.txt: {e}")

if __name__ == "__main__":
    main()
