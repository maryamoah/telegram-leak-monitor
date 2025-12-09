import os
import sqlite3
import requests
from telethon import TelegramClient, events
from config import API_ID, API_HASH, PHONE, CHANNELS, FORWARD_URL, DOWNLOAD_PATH

SESSION_FILE = "/session_storage/scraper.session"


# ---------------------------------------------------------
# PERMANENT FIX: Auto-detect and repair locked/corrupted
# Telethon session (SQLite). Prevents "database is locked".
# ---------------------------------------------------------
def ensure_session_ok():
    # If no session exists yet, nothing to clean
    if not os.path.exists(SESSION_FILE):
        return

    try:
        # Try checking database integrity
        conn = sqlite3.connect(SESSION_FILE)
        conn.execute("PRAGMA integrity_check;")
        conn.close()

    except Exception as e:
        print("⚠️  Session file corrupted or locked:", e)
        print("🧹 Resetting Telethon session...")

        try:
            os.remove(SESSION_FILE)
        except FileNotFoundError:
            pass

        # Delete SQLite journal file if present
        journal = SESSION_FILE + "-journal"
        if os.path.exists(journal):
            os.remove(journal)

        print("✅ Session reset completed.")


# Apply fix BEFORE creating the client
ensure_session_ok()

# Create Telethon client AFTER session confirmed safe
client = TelegramClient(SESSION_FILE, API_ID, API_HASH)


async def start_scraper():
    await client.start(PHONE)

    print(f"Signed in and watching {len(CHANNELS)} channels...")
    print("Listening for new messages...")

    # Event listener for new messages
    @client.on(events.NewMessage(chats=CHANNELS))
    async def handler(event):
        msg = event.message

        # File handling
        if msg.file:
            filename = f"{msg.id}_{msg.file.name}"
            filepath = os.path.join(DOWNLOAD_PATH, filename)
            await msg.download_media(filepath)
            print(f"[+] Downloaded: {filepath}")

            requests.post(FORWARD_URL, json={"filepath": filepath})

        # Text handling
        if msg.text:
            requests.post(FORWARD_URL, json={"text": msg.text})

    await client.run_until_disconnected()


# Standard Telethon startup
with client:
    client.loop.run_until_complete(start_scraper())
