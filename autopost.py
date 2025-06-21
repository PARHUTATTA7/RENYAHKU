import asyncio
from telegram import Bot
import os
from pathlib import Path
import requests
from datetime import datetime, timedelta
import pytz
import re

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
FOOTER = env.get("FOOTER", "###MAU BERLANGGANAN IPTV LIVE EVENT UPTODATA####")

bot = Bot(token=BOT_TOKEN)

def fetch_jadwal():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://thedaddy.click/",
            "Accept": "application/json, text/plain, */*"
        }
        response = requests.get(API_URL, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        tz_uk = pytz.timezone("Europe/London")
        tz_jkt = pytz.timezone("Asia/Jakarta")
        now_uk = datetime.now(tz_uk).date()
        now_jkt = datetime.now(tz_jkt)

        # Temukan key berdasarkan tanggal UK
        target_key = None
        for k in data.keys():
            match = re.search(r"\d{1,2}(st|nd|rd|th)?\s+\w+\s+\d{4}", k)
            if match:
                clean_date = re.sub(r"(st|nd|rd|th)", "", match.group(0))
                dt = datetime.strptime(clean_date, "%d %B %Y").date()
                if dt == now_uk:
                    target_key = k
                    break

        if not target_key:
            return "⚠️ Tidak ada jadwal untuk hari ini."

        events_by_type = data.get(target_key)
        if not isinstance(events_by_type, dict):
            return f"⚠️ Format data salah untuk key: {target_key}"

        message = f"📅 *{target_key}* _(WIB)_\n\n"
        total = 0

        for category, events in events_by_type.items():
            added = 0
            section = f"🗂️ *{category}*\n"

            for e in events:
                time_str = e.get("time")
                title = e.get("event")
                channels = e.get("channels", []) + e.get("channels2", [])

                try:
                    # Ambil jam dari UK
                    h, m = map(int, time_str.split(":"))
                    dt_uk = tz_uk.localize(now_jkt.replace(hour=h, minute=m, second=0, microsecond=0))
                    dt_jkt = dt_uk.astimezone(tz_jkt)

                    if dt_jkt < now_jkt or dt_jkt > now_jkt + timedelta(hours=2):
                        continue

                    ch_names = ', '.join(c.get("channel_name") for c in channels if c.get("channel_name"))
                    section += f"⏰ {dt_jkt.strftime('%H:%M')} WIB\n🎯 {title}\n📺 {ch_names or 'N/A'}\n\n"
                    added += 1
                except Exception as err:
                    print(f"⚠️ Error parsing waktu: {time_str} → {err}")
                    continue

            if added:
                message += section + "\n"
                total += added

        if total == 0:
            return "⚠️ Tidak ada pertandingan 2 jam ke depan."

        message += FOOTER.strip()
        return message.strip()

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
