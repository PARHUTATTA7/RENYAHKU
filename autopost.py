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

def split_message(text, max_len=4000):
    chunks = []
    while len(text) > max_len:
        split_at = text.rfind('\n\n', 0, max_len)
        if split_at == -1:
            split_at = max_len
        chunks.append(text[:split_at].strip())
        text = text[split_at:].strip()
    chunks.append(text)
    return chunks

env = load_env(BOTDATA_FILE)
API_URL = env.get("API_URL")
BOT_TOKEN = env.get("BOT_TOKEN")
CHAT_IDS = [x.strip() for x in env.get("CHAT_ID", "").split(",") if x.strip()]
FOOTER = env.get("FOOTER_MSG", "").strip()
WINDOW_HOURS = 2

bot = Bot(token=BOT_TOKEN)

def fetch_jadwal():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://thedaddy.click/",
            "Accept": "application/json"
        }
        response = requests.get(API_URL, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        tz_uk = pytz.timezone("Europe/London")
        tz_jkt = pytz.timezone("Asia/Jakarta")
        today_uk = datetime.now(tz_uk).date()
        now_jkt = datetime.now(tz_jkt)

        # Temukan key tanggal UK = hari ini
        target_key = None
        for k in data.keys():
            match = re.search(r"\d{1,2}(st|nd|rd|th)?\s+\w+\s+\d{4}", k)
            if match:
                try:
                    clean_date = re.sub(r"(st|nd|rd|th)", "", match.group(0))
                    dt = datetime.strptime(clean_date, "%d %B %Y").date()
                    if dt == today_uk:
                        target_key = k
                        break
                except Exception as e:
                    print(f"⚠️ Gagal parse tanggal dari '{k}': {e}")

        if not target_key:
            return [f"⚠️ Tidak ada jadwal untuk tanggal {today_uk.strftime('%d %B %Y')}"]

        events_by_type = data.get(target_key)
        if not isinstance(events_by_type, dict):
            return [f"⚠️ Format data salah untuk key: {target_key}"]

        base_message = f"📅 *{target_key}* _(WIB)_\n\n"
        message = base_message
        total = 0

        for category, events in events_by_type.items():
            if category.lower() == "tv shows":
                continue  # Lewati kategori TV Shows

            section = f"🗂️ *{category}*\n"
            added = 0

            for e in events:
                time_str = e.get("time")
                title = e.get("event")

                ch1 = e.get("channels", [])
                ch2 = e.get("channels2", [])
                if isinstance(ch1, dict): ch1 = [ch1]
                if not isinstance(ch1, list): ch1 = []
                if isinstance(ch2, dict): ch2 = [ch2]
                if not isinstance(ch2, list): ch2 = []
                channels = ch1 + ch2

                try:
                    h, m = map(int, time_str.split(":"))
                    dt_naive = datetime.combine(today_uk, datetime.min.time()).replace(hour=h, minute=m)
                    dt_uk = tz_uk.localize(dt_naive)
                    dt_jkt = dt_uk.astimezone(tz_jkt)

                    if dt_jkt < now_jkt or dt_jkt > now_jkt + timedelta(hours=WINDOW_HOURS):
                        continue

                    seen = set()
                    ch_names = ', '.join(
                        c["channel_name"] for c in channels
                        if c.get("channel_name") and not (c["channel_name"] in seen or seen.add(c["channel_name"]))
                    )

                    section += f"⏰ {dt_jkt.strftime('%H:%M')} WIB\n🎯 {title}\n📺 {ch_names or 'N/A'}\n\n"
                    added += 1
                except Exception as err:
                    print(f"⚠️ Error parsing event: {time_str} → {err}")
                    continue

            if added:
                message += section + "\n"
                total += added

        if total == 0:
            return ["⚠️ Tidak ada pertandingan dalam 2 jam ke depan."]

        message += FOOTER.strip()
        return split_message(message.strip())

    except Exception as e:
        return [f"❌ Gagal mengambil data: {e}"]

async def main():
    messages = fetch_jadwal()
    for chat_id in CHAT_IDS:
        for part in messages:
            try:
                await bot.send_message(chat_id=chat_id, text=part, parse_mode='Markdown')
                print(f"✅ Terkirim ke {chat_id}")
            except Exception as e:
                print(f"❌ Gagal kirim ke {chat_id}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
