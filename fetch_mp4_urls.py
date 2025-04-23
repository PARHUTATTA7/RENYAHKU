import yt_dlp
import os
import json
import base64
import subprocess

# Fungsi untuk mendapatkan URL MP4 atau M3U8
def get_video_url(youtube_url):
    # Mengambil cookie dari environment variable GitHub
    cookie_str = os.getenv('YT_COOKIE')  # Cookie yang disimpan di GitHub Secrets sebagai YT-COOKIE
    
    # Jika cookie tersedia, decode dan load cookies
    if cookie_str:
        try:
            cookie_data = base64.b64decode(cookie_str).decode('utf-8')  # Decode jika cookie disimpan sebagai base64 string
            cookies = json.loads(cookie_data)  # Mengonversi string JSON ke dictionary
        except Exception as e:
            print(f"Error decoding or loading cookies: {e}")
            cookies = []
    else:
        print("No cookies found in environment.")
        cookies = []

    # Opsi untuk yt-dlp
    ydl_opts = {
        'format': 'bestaudio/best',  # Mengambil kualitas terbaik
        'quiet': False,  # Menampilkan output dari yt-dlp untuk debugging
        'noplaylist': True,  # Tidak ikut playlist
        'geo_bypass': True,  # Melewati pembatasan geografis
        'geo_bypass_country': 'US',  # Mengatur negara ke US
        'cookies': cookies,  # Menggunakan cookies yang didekode
    }

    try:
        # Memanggil yt-dlp untuk mengekstrak informasi video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(youtube_url, download=False)
            video_url = None
            print(f"info_dict: {info_dict}")  # Debug info_dict untuk memeriksa data yang diterima

            # Cek format yang tersedia
            for format in info_dict['formats']:
                if 'mp4' in format['ext']:
                    video_url = format['url']
                    video_format = 'mp4'
                    print(f"Found MP4 URL: {video_url}")  # Debug untuk melihat MP4 URL yang ditemukan
                    break
                elif 'm3u8' in format['ext']:
                    video_url = format['url']
                    video_format = 'm3u8'
                    print(f"Found M3U8 URL: {video_url}")  # Debug untuk melihat M3U8 URL yang ditemukan
                    break
            
            if video_url:
                return f"{info_dict['title']}.{video_format}", video_url
            else:
                return "No suitable video format found", None
    except Exception as e:
        print(f"Error with yt-dlp for {youtube_url}: {e}")
        return "Error fetching video URL", None

# Fungsi untuk memproses daftar video dari file
def process_video_list(file_path):
    try:
        with open(file_path, 'r') as file:
            youtube_urls = file.readlines()
    except FileNotFoundError:
        print(f"Error: File {file_path} not found.")
        return []

    print(f"Found {len(youtube_urls)} URLs in {file_path}")
    
    video_info = []
    for youtube_url in youtube_urls:
        youtube_url = youtube_url.strip()  # Hapus spasi ekstra
        if youtube_url:
            print(f"Processing URL: {youtube_url}")
            try:
                video_name, video_url = get_video_url(youtube_url)
                print(f"Video Name: {video_name}, Video URL: {video_url}")  # Debugging hasil dari get_video_url
                video_info.append((video_name, video_url))  # Menyimpan nama dan URL
            except Exception as e:
                print(f"Failed to process {youtube_url}: {e}")
                video_info.append(("ERROR", None))
        else:
            print("Empty line detected, skipping.")
    
    return video_info

# Fungsi untuk push hasil ke repository GitHub
def git_push(output_file_path):
    try:
        # Menambahkan file ke staging area
        subprocess.run(["git", "add", output_file_path], check=True)
        
        # Commit perubahan dengan pesan
        subprocess.run(["git", "commit", "-m", "Update video URLs"], check=True)
        
        # Push perubahan ke repository GitHub
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print(f"Successfully pushed {output_file_path} to GitHub.")
    except subprocess.CalledProcessError as e:
        print(f"Error during git push: {e}")

# Fungsi utama untuk menjalankan script
if __name__ == "__main__":
    file_path = "list.txt"  # Ganti dengan path file list.txt kamu
    video_info = process_video_list(file_path)
    
    # Menyimpan hasil ke dalam file output yang sesuai dengan format
    for video_name, video_url in video_info:
        if video_url:  # Jika URL berhasil didapatkan
            # Menyimpan sebagai file .m3u8 jika formatnya m3u8
            if "m3u8" in video_url:
                output_file_path = f"github/namarepo/{video_name}.m3u8"
            else:
                # Menyimpan sebagai file .mp4 jika formatnya mp4
                output_file_path = f"github/namarepo/{video_name}.mp4"
            
            # Menyimpan hasil ke dalam file output
            with open(output_file_path, "w") as f:
                f.write(video_url + "\n")

            print(f"Process completed. Output saved to {output_file_path}.")
            
            # Push hasil ke GitHub repository
            git_push(output_file_path)
        else:
            print(f"Skipping {video_name}, no video URL found.")
