import yt_dlp

def get_mp4_url(youtube_url):
    # Menyeting opsi yt-dlp dengan file cookies yang diekspor
    ydl_opts = {
        'format': 'bestaudio/best',  # Mengambil kualitas terbaik
        'quiet': False,  # Menampilkan output dari yt-dlp untuk debugging
        'noplaylist': True,  # Tidak ikut playlist
        'geo_bypass': True,  # Melewati pembatasan geografis
        'geo_bypass_country': 'US',  # Mengatur negara ke US
        'cookies': 'path_to_your_cookies_file.json',  # Ganti dengan path ke file cookies yang diekspor
    }

    try:
        # Memanggil yt-dlp untuk mengekstrak informasi video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(youtube_url, download=False)
            mp4_url = None
            print(f"info_dict: {info_dict}")  # Debug info_dict untuk memeriksa data yang diterima

            # Cek format yang tersedia
            for format in info_dict['formats']:
                if 'mp4' in format['ext']:
                    mp4_url = format['url']
                    print(f"Found MP4 URL: {mp4_url}")  # Debug untuk melihat MP4 URL yang ditemukan
                    break
            
            if mp4_url:
                return mp4_url
            else:
                return "No MP4 available"
    except Exception as e:
        print(f"Error with yt-dlp for {youtube_url}: {e}")
        return "Error fetching MP4 URL"

def process_video_list(file_path):
    try:
        with open(file_path, 'r') as file:
            youtube_urls = file.readlines()
    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
        return []

    print(f"Found {len(youtube_urls)} URLs in {file_path}")
    
    urls = []
    for youtube_url in youtube_urls:
        youtube_url = youtube_url.strip()  # Hapus spasi ekstra
        if youtube_url:
            print(f"Processing URL: {youtube_url}")
            try:
                mp4_url = get_mp4_url(youtube_url)
                print(f"MP4 URL: {mp4_url}")  # Debugging hasil dari get_mp4_url
                urls.append(mp4_url)
            except Exception as e:
                print(f"Failed to process {youtube_url}: {e}")
                urls.append("ERROR")
        else:
            print("Empty line detected, skipping.")
    
    return urls

if __name__ == "__main__":
    file_path = "public/list.txt"  # Ganti dengan path file list.txt kamu
    mp4_urls = process_video_list(file_path)
    
    # Membuat folder jika belum ada
    os.makedirs("public/urls", exist_ok=True)

    # Menyimpan hasil ke dalam file output.txt
    with open("public/urls/output.txt", "w") as f:
        for url in mp4_urls:
            f.write(url + "\n")

    print(f"Process completed. Output saved to public/urls/output.txt.")
