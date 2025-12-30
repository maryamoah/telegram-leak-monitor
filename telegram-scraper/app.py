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
        print("Session OK", flush=True)
    except Exception as e:
        print("Session damaged, resetting:", e, flush=True)
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

    print(f"Signed in and watching {len(CHANNELS)} channels", flush=True)
    print(f"Channels: {CHANNELS}", flush=True)
    print("Listening for new messages...", flush=True)

    @client.on(events.NewMessage(chats=CHANNELS))
    async def handler(event):
        msg = event.message
        print(f"[i] New message received (id={msg.id})", flush=True)

        # ==========================================
        # FILE HANDLING ONLY
        # ==========================================
        if msg.file:
            filename = f"{msg.id}_{msg.file.name}"
            filepath = os.path.join(DOWNLOAD_PATH, filename)

            await msg.download_media(filepath)
            print(f"[+] Downloaded: {filepath}", flush=True)

            try:
                requests.post(
                    FORWARD_URL,
                    json={"filepath": filepath},
                    timeout=10
                )
            except Exception as e:
                print(f"[!] Extractor error: {e}", flush=True)

    await client.run_until_disconnected()


with client:
    client.loop.run_until_complete(start_scraper())
