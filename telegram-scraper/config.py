import os

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
PHONE = os.getenv("TELEGRAM_PHONE")
CHANNELS = [c.strip() for c in os.getenv("TARGET_CHANNELS", "").split(",")]
FORWARD_URL = os.getenv("FORWARD_URL")
DOWNLOAD_PATH = "/files"
