import os
import requests
from logger import logger   # reuse your existing logger

def notify_n8n(domain, filename, matches):
    webhook = os.getenv("N8N_WEBHOOK")

    if not matches:
        logger.debug(f"No domain matches in {filename}")
        return

    if not webhook:
        logger.warning("N8N_WEBHOOK not set, skipping n8n notification")
        return

    payload = {
        "domain": domain,
        "file": filename,
        "count": len(matches),
        "emails": [m["email"] for m in matches[:5]]
    }

    try:
        requests.post(webhook, json=payload, timeout=10)
        logger.info(f"n8n notified for {filename} ({len(matches)} matches)")
    except Exception as e:
        logger.error(f"Failed to notify n8n: {e}")
