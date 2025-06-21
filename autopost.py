import asyncio
from telegram import Bot
import os
from pathlib import Path
import requests

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
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
            "Referer": "https://thedaddy.click/",
            "Accept": "application/json, text/plain, */*"
        }

        response = requests.get(API_URL, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data:
            return "⚠️ Tidak ada jadwal hari ini."

        # Ambil key pertama (tanggal)
        first_key = list(data.keys())[0]
        events = data[first_key].get("PPV Events", [])
        if not events:
            return "⚠️ Tidak ada event hari ini."

        message = f"📅 *{first_key}* _(WIB)_\n\n"

        from datetime import datetime, timedelta
        import pytz

        tz_jakarta = pytz.timezone("Asia/Jakarta")
        tz_uk = pytz.timezone("Europe/London")
        now = datetime.now(tz_jakarta)

        count = 0
        for e in events:
            time_str = e.get("time", "-")
            event_title = e.get("event", "-")
            channel_names = ", ".join([c.get("channel_name") for c in e.get("channels", [])])

            try:
                dt_uk = datetime.strptime(time_str, "%H:%M")
                dt_uk = tz_uk.localize(now.replace(hour=dt_uk.hour, minute=dt_uk.minute, second=0))
                dt_jakarta = dt_uk.astimezone(tz_jakarta)

                if dt_jakarta.date() != now.date():
                    continue
                if dt_jakarta < now - timedelta(minutes=60) or dt_jakarta > now + timedelta(hours=1):
                    continue

                jam = dt_jakarta.strftime("%H:%M")
                message += f"⏰ {jam} WIB\n🎯 *{event_title}*\n📺 {channel_names or 'N/A'}\n\n"
                count += 1

            except Exception as e:
                print(f"⚠️ Gagal parsing waktu: {time_str} → {e}")
                continue

        return message if count > 0 else "⚠️ Tidak ada pertandingan tersisa hari ini."

    except Exception as e:
        return f"❌ Gagal mengambil data: {e}"

async def main():
    message = fetch_jadwal()
    for chat_id in CHAT_IDS:
        try:
            await bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
            print(f"✅ Terkirim ke {chat_id}")
        except Exception as e:
            print(f"❌ Gagal kirim ke {chat_id}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
