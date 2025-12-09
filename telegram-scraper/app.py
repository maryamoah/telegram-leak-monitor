import os
import asyncio
import requests
import sqlite3
from telethon import TelegramClient, events
from config import API_ID, API_HASH, PHONE, CHANNELS, FORWARD_URL, DOWNLOAD_PATH, FILTER_URL

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
#  Helper: send payload to filter-engine safely
# ----------------------------------------------------------
def forward_to_filter(data):
    try:
        resp = requests.post(FILTER_URL, json=data, timeout=5)
        print(f"[→ FILTER] {data}  (status {resp.status_code})")
    except Exception as e:
        print(f"[!] Failed to forward to filter-engine: {e}")


# ----------------------------------------------------------
#  MAIN SCRAPER
# ----------------------------------------------------------
async def start_scraper():
    await client.start(PHONE)

    print(f"Signed in and watching {len(CHANNELS)} channels...")
    print("Listening for new messages...")

    @client.on(events.NewMessage(chats=CHANNELS))
    async def handler(event):
        msg = event.message

        # ==============================================
        # 1️⃣ FILE HANDLING
        # ==============================================
        if msg.file:
            filename = f"{msg.id}_{msg.file.name}"
            filepath = os.path.join(DOWNLOAD_PATH, filename)

            await msg.download_media(filepath)
            print(f"[+] Downloaded: {filepath}")

            # Send file to extractor
            try:
                extract_resp = requests.post(FORWARD_URL, json={"filepath": filepath})
                extracted = extract_resp.json() if extract_resp.status_code == 200 else {}
            except Exception as e:
                print(f"[!] Extractor error: {e}")
                return

            # Forward extracted emails to filter-engine
            if "emails" in extracted:
                forward_to_filter({"emails": extracted["emails"]})

        # ==============================================
        # 2️⃣ TEXT ONLY HANDLING
        # ==============================================
        if msg.text:
            try:
                extract_resp = requests.post(FORWARD_URL, json={"text": msg.text})
                extracted = extract_resp.json() if extract_resp.status_code == 200 else {}
            except Exception as e:
                print(f"[!] Extractor error: {e}")
                return

            if "emails" in extracted:
                forward_to_filter({"emails": extracted["emails"]})

    await client.run_until_disconnected()


# ----------------------------------------------------------
#  Start client
# ----------------------------------------------------------
with client:
    client.loop.run_until_complete(start_scraper())
