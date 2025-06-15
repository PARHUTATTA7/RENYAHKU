import subprocess

def get_twitch_m3u8_url(channel_name):
    try:
        # Jalankan perintah streamlink dan ambil hasilnya
        result = subprocess.run(
            ['streamlink', f'https://twitch.tv/{channel_name}', 'best', '--stream-url'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print("Gagal mendapatkan URL M3U8:")
        print(e.stderr)
        return None

# Ganti dengan nama channel Twitch yang kamu inginkan
channel = 'sriwijayatvonline'
m3u8_url = get_twitch_m3u8_url(channel)

if m3u8_url:
    print("M3U8 URL ditemukan:")
    print(m3u8_url)
else:
    print("Tidak dapat mengambil URL.")
