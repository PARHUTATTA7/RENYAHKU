from telegram import Bot
import os
from pathlib import Path
import requests

# Path ke file data rahasia
BOTDATA_FILE = Path.home() / "botdata.txt"

def load_env(file_path):
    data = {}
    with open(file_path, "r") as f:
        for line in f:
            if "=" in line:
                key, val = line.strip().split("=", 1)
                data[key.strip()] = val.strip()
    return data

env = load_env(BOTDATA_FILE)

API_URL = env.get("API_URL")
BOT_TOKEN = env.get("BOT_TOKEN")
CHAT_IDS = [x.strip() for x in env.get("CHAT_ID", "").split(",") if x.strip()]

bot = Bot(token=BOT_TOKEN)

def fetch_jadwal():
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data:
            return "⚠️ Tidak ada jadwal hari ini."

        message = "📅 *Jadwal Pertandingan Hari Ini:*\n\n"
        for match in data:
            waktu = match.get("time", "-")
            liga = match.get("league", "-")
            pertandingan = match.get("match", "-")
            message += f"⏰ {waktu} | *{liga}*\n⚽️ {pertandingan}\n\n"

        return message.strip()

    except Exception as e:
        return f"❌ Gagal mengambil data: {e}"

def main():
    message = fetch_jadwal()
    for chat_id in CHAT_IDS:
        try:
            bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
            print(f"✅ Terkirim ke {chat_id}")
        except Exception as e:
            print(f"❌ Gagal kirim ke {chat_id}: {e}")

if __name__ == "__main__":
    main()
