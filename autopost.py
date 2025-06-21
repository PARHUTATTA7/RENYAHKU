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
FOOTER_MSG = env.get("FOOTER_MSG", "")
WINDOW_HOURS = 2

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

        # Ambil tanggal sekarang di UK timezone
        tz_uk = pytz.timezone("Europe/London")
        tz_jakarta = pytz.timezone("Asia/Jakarta")
        today_uk = datetime.now(tz_uk).date()
        now_jakarta = datetime.now(tz_jakarta)
        print(f"[DEBUG] Sekarang WIB: {now_jakarta.strftime('%Y-%m-%d %H:%M:%S')}")

        # Temukan key dengan tanggal UK hari ini
        target_key = None
        for k in data.keys():
            match = re.search(r"\d{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4}", k)
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
            return "⚠️ Tidak menemukan jadwal untuk hari ini di data."

        events_by_type = data[target_key]

        all_events = []
        for group_name, group_events in events_by_type.items():
            print(f"[DEBUG] Menambahkan {len(group_events)} event dari grup '{group_name}'")
            for ev in group_events:
                ev["__group__"] = group_name
                all_events.append(ev)

        if not all_events:
            return "⚠️ Tidak ada event hari ini."

        message = f"📅 *{target_key}* _(WIB)_\n\n"
        count = 0
        last_group = None

        for e in all_events:
            group_name = e.get("__group__", "Unknown")
            time_str = e.get("time", "-")
            event_title = e.get("event", "-")
            channel_names = ", ".join([c.get("channel_name") for c in e.get("channels", [])])

            try:
                dt_naive = datetime.strptime(time_str, "%H:%M")
                dt_uk = tz_uk.localize(datetime.combine(today_uk, dt_naive.time()))
                dt_jakarta = dt_uk.astimezone(tz_jakarta)

                if dt_jakarta.date() != now_jakarta.date():
                    if not (dt_jakarta.hour < 4 and (dt_jakarta.date() - now_jakarta.date()).days == 1):
                        continue
                if dt_jakarta < now_jakarta - timedelta(minutes=5):
                    continue
                if dt_jakarta > now_jakarta + timedelta(hours=WINDOW_HOURS):
                    continue

                if group_name != last_group:
                    message += f"🗂️ *{group_name}*\n"
                    last_group = group_name

                jam = dt_jakarta.strftime("%H:%M")
                message += f"⏰ {jam} WIB\n🎯 *{event_title}*\n📺 {channel_names or 'N/A'}\n\n"
                count += 1

            except Exception as e:
                print(f"⚠️ Gagal parsing waktu: {time_str} → {e}")
                continue

        if count > 0:
            if FOOTER_MSG:
                message += f"\n{FOOTER_MSG}"
            return message.strip()
        else:
            return "⚠️ Tidak ada pertandingan dalam 2 jam ke depan."

    except Exception as e:
        return f"❌ Gagal mengambil data: {e}"

async def main():
    print(f"[DEBUG] API_URL: {API_URL}")
    print(f"[DEBUG] CHAT_IDS: {CHAT_IDS}")
    message = fetch_jadwal()

    for chat_id in CHAT_IDS:
        try:
            await bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
            print(f"✅ Terkirim ke {chat_id}")
        except Exception as e:
            print(f"❌ Gagal kirim ke {chat_id}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
