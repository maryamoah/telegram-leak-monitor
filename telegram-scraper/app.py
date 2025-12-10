import os
import asyncio
import requests
import sqlite3
from telethon import TelegramClient, events
from config import API_ID, API_HASH, PHONE, CHANNELS, FORWARD_URL, DOWNLOAD_PATH

SESSION_FILE = "/session_storage/scraper.session"


# ----------------------------------------------------------
#  Auto-fix locked/corrupt Telethon session
# ----------------------------------------------------------
def ensure_session_clean():
    try:
        conn = sqlite3.connect(SESSION_FILE)
        conn.execute("SELECT 1;")
        conn.close()
        print("Session OK")
    except Exception as e:
        print("Session damaged, resetting:", e)
        try:
            os.remove(SESSION_FILE)
        except:
            pass


ensure_session_clean()
client = TelegramClient(SESSION_FILE, API_ID, API_HASH)


# ----------------------------------------------------------
# MAIN SCRAPER
# ----------------------------------------------------------
async def start_scraper():
    await client.start(PHONE)

    print(f"Signed in and watching {len(CHANNELS)} channels...")
    print("Listening for new messages...")

    @client.on(events.NewMessage(chats=CHANNELS))
    async def handler(event):
        msg = event.message

        # ==========================================
        # 1️⃣ FILE HANDLING
        # ==========================================
        if msg.file:
            filename = f"{msg.id}_{msg.file.name}"
            filepath = os.path.join(DOWNLOAD_PATH, filename)

            await msg.download_media(filepath)
            print(f"[+] Downloaded: {filepath}")

            # Send file path to extractor
            try:
                requests.post(FORWARD_URL, json={"filepath": filepath}, timeout=10)
            except Exception as e:
                print(f"[!] Extractor error: {e}")

        # ==========================================
        # 2️⃣ TEXT ONLY HANDLING
        # ==========================================
        if msg.text:
            try:
                requests.post(FORWARD_URL, json={"text": msg.text}, timeout=10)
            except Exception as e:
                print(f"[!] Extractor error: {e}")

    await client.run_until_disconnected()


with client:
    client.loop.run_until_complete(start_scraper())
