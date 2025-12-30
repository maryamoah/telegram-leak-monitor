import os
import requests
from logger import logger

# =========================================================
# N8N NOTIFIER
# =========================================================

def notify_n8n(
    source: str,
    emails: list,
    creds: list | None = None,
    max_preview: int = 5,
):
    """
    Forward a summary notification to n8n.

    Assumes:
      - emails are already scoped & validated upstream
      - creds (if present) are dicts with email/password
    """

    webhook = os.getenv("N8N_WEBHOOK")

    if not emails and not creds:
        logger.debug(f"No data to notify for {source}")
        return

    if not webhook:
        logger.warning("N8N_WEBHOOK not set, skipping n8n notification")
        return

    preview_emails = sorted(set(emails))[:max_preview]

    payload = {
        "source": source,
        "emails": preview_emails,
        "email_count": len(set(emails)),
    }

    if creds:
        payload["cred_count"] = len(creds)

    try:
        requests.post(webhook, json=payload, timeout=10)
        logger.info(
            f"n8n notified for {source} "
            f"({payload.get('email_count', 0)} emails, "
            f"{payload.get('cred_count', 0)} creds)"
        )
    except Exception as e:
        logger.error(f"Failed to notify n8n for {source}: {e}")
