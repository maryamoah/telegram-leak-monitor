import os
import asyncio
import requests
from telethon import TelegramClient, events
from config import API_ID, API_HASH, PHONE, CHANNELS, FORWARD_URL, DOWNLOAD_PATH

SESSION_FILE = "/session_storage/scraper.session"
client = TelegramClient(SESSION_FILE, API_ID, API_HASH)

async def start_scraper():
    await client.start(PHONE)
    print(f"Signed in and watching {len(CHANNELS)} channels...")
    
    # Register event listener for NEW messages
    @client.on(events.NewMessage(chats=CHANNELS))
    async def handler(event):
        msg = event.message

        # If there is a file → download it
        if msg.file:
            filename = f"{msg.id}_{msg.file.name}"
            filepath = os.path.join(DOWNLOAD_PATH, filename)
            await msg.download_media(filepath)
            print(f"[+] Downloaded: {filepath}")
            
            # Send file to extractor
            requests.post(FORWARD_URL, json={"filepath": filepath})
        
        # If just text → send text for extraction
        if msg.text:
            requests.post(FORWARD_URL, json={"text": msg.text})

    print("Listening for new messages...")
    await client.run_until_disconnected()

with client:
    client.loop.run_until_complete(start_scraper())
