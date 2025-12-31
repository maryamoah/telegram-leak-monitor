import os
import asyncio
import requests
import sqlite3

from telethon import TelegramClient, events
from telethon.errors import InviteHashExpiredError

from config import API_ID, API_HASH, PHONE, CHANNELS, FORWARD_URL, DOWNLOAD_PATH

SESSION_FILE = "/session_storage/scraper.session"

# ----------------------------------------------------------
# Auto-fix locked/corrupt Telethon session
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
        except Exception:
            pass


ensure_session_clean()
client = TelegramClient(SESSION_FILE, API_ID, API_HASH)

# ----------------------------------------------------------
# Validate channels before listening
# ----------------------------------------------------------
async def resolve_valid_channels(client, channels):
    valid = []

    for ch in channels:
        try:
            await client.get_input_entity(ch)
            valid.append(ch)
        except InviteHashExpiredError:
            print(f"[!] Skipping expired invite link: {ch}", flush=True)
        except Exception as e:
            print(f"[!] Skipping invalid channel {ch}: {e}", flush=True)

    return valid

# ----------------------------------------------------------
# MAIN SCRAPER
# ----------------------------------------------------------
async def start_scraper():
    await client.start(PHONE)

    valid_channels = await resolve_valid_channels(client, CHANNELS)

    if not valid_channels:
        print("[!] No valid Telegram channels left to watch. Exiting.", flush=True)
        return

    print(f"Signed in and watching {len(valid_channels)} channels", flush=True)
    print(f"Channels: {valid_channels}", flush=True)
    print("Listening for new messages...", flush=True)

    @client.on(events.NewMessage(chats=valid_channels))
    async def handler(event):
        msg = event.message
        print(f"[i] New message received (id={msg.id})", flush=True)

        # ==========================================
        # FILE HANDLING ONLY
        # ==========================================
        if not msg.file:
            return

        filename = f"{msg.id}_{msg.file.name}"
        filepath = os.path.join(DOWNLOAD_PATH, filename)

        try:
            await msg.download_media(filepath)
            print(f"[+] Downloaded: {filepath}", flush=True)
        except Exception as e:
            print(f"[!] Download failed: {e}", flush=True)
            return

        try:
            requests.post(
                FORWARD_URL,
                json={"filepath": filepath},
                timeout=10
            )
            print(f"[+] Forwarded to extractor: {filepath}", flush=True)
        except Exception as e:
            print(f"[!] Extractor error: {e}", flush=True)

    await client.run_until_disconnected()


with client:
    client.loop.run_until_complete(start_scraper())
