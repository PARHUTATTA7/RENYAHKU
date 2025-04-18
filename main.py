def process_video_list(file_path):
    with open(file_path, 'r') as file:
        youtube_urls = file.readlines()
    
    urls = []
    for youtube_url in youtube_urls:
        youtube_url = youtube_url.strip()  # Hapus spasi ekstra
        if youtube_url:
            try:
                mp4_url = get_mp4_url(youtube_url)
                urls.append(mp4_url)
            except Exception as e:
                print(f"Failed to process {youtube_url}: {e}")
                urls.append("ERROR")
    return urls

if __name__ == "__main__":
    file_path = "public/list.txt"  # Ganti dengan path file list.txt kamu
    mp4_urls = process_video_list(file_path)
    
    # Menyimpan hasil ke dalam file output
    with open("public/urls/output.txt", "w") as f:
        for url in mp4_urls:
            f.write(url + "\n")
