import os
import requests
from telethon import TelegramClient, events
from config import API_ID, API_HASH, PHONE, CHANNELS, FORWARD_URL, DOWNLOAD_PATH

SESSION_FILE = "/session_storage/scraper.session"
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

with client:
    client.loop.run_until_complete(start_scraper())
    
if __name__ == "__main__":
    import time
    print("Scraper container started. Waiting...")
    while True:
        time.sleep(10)
    
