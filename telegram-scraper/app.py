import os
import asyncio
import requests
from telethon import TelegramClient
from config import API_ID, API_HASH, PHONE, CHANNELS, FORWARD_URL, DOWNLOAD_PATH

client = TelegramClient("scraper", API_ID, API_HASH)

async def main():
    await client.start(PHONE)
    print(f"Watching {len(CHANNELS)} channels...")

    for channel in CHANNELS:
        async for msg in client.iter_messages(channel, reverse=True):
            if msg.file:
                filename = f"{msg.id}_{msg.file.name}"
                filepath = os.path.join(DOWNLOAD_PATH, filename)

                await msg.download_media(filepath)
                print(f"[+] Downloaded: {filepath}")

                requests.post(FORWARD_URL, json={"filepath": filepath})

with client:
    client.loop.run_until_complete(main())
