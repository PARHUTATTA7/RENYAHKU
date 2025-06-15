import subprocess

def get_twitch_m3u8_url(channel_name):
    try:
        # Jalankan streamlink dan ambil URL stream
        result = subprocess.run(
            ['streamlink', f'https://twitch.tv/{channel_name}', 'best', '--stream-url'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print("❌ Gagal mendapatkan URL M3U8:")
        print(e.stderr)
        return None

if __name__ == "__main__":
    channel = 'sriwijayatvonline'
    m3u8_url = get_twitch_m3u8_url(channel)

    if m3u8_url:
        print("✅ M3U8 URL ditemukan:")
        print(m3u8_url)
        # Simpan ke file
        try:
            with open("twitch_url.txt", "w") as f:
                f.write(m3u8_url + "\n")
            print("✅ Disimpan ke twitch_url.txt")
        except Exception as e:
            print("❌ Gagal menulis ke file:", e)
    else:
        print("⚠️ Tidak dapat mengambil URL.")
