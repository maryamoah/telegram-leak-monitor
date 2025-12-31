# Telegram Leak Monitor – Automated Threat Intelligence Pipeline

![Status](https://img.shields.io/badge/status-active-success?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)
![Docker](https://img.shields.io/badge/Docker-Containerized-blue?style=for-the-badge&logo=docker)
![Slack](https://img.shields.io/badge/Slack-Alerts-4A154B?style=for-the-badge&logo=slack)
![n8n](https://img.shields.io/badge/n8n-Automation-orange?style=for-the-badge&logo=n8n)
![Telethon](https://img.shields.io/badge/Telethon-Telegram_API-blue?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

This project monitors Telegram channels for leaked content, downloads shared files, extracts **emails and credentials**, filters academic-domain exposure (e.g. `@example.edu`), validates credentials, and sends **aggregated SOC alerts** to Slack via n8n.

---

## Pipeline

```
Telegram → Scraper → Extractor → Filter → n8n → Slack
```

**Use case:**  
Automatically detect leaked university accounts and credentials circulating in Telegram communities while reducing alert noise and duplication.

---

## Architecture

```
+---------------------+       +---------------------+       +---------------------+
| Telegram Scraper    | ----> | Extractor Engine    | ----> | Filter Engine       |
| (Telethon)          |       | Extracts emails &   |       | Applies domain      |
| Downloads files     |       | credentials from    |       | and scope rules     |
+---------------------+       | large files         |       +---------------------+
                                         |
                                         v
                             +-------------------------+
                             | n8n Automation          |
                             | Validates credentials, |
                             | aggregates results,    |
                             | sends Slack alerts     |
                             +-------------------------+
                                         |
                                         v
                              +------------------------+
                              | Slack Notification     |
                              +------------------------+
```

---

## Repository Structure

```
telegram-leak-monitor/
│
├── telegram-scraper/
│   ├── app.py
│   ├── config.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── extractor-engine/
│   ├── app.py
│   ├── extractor.py
│   ├── scripts/
│   │   └── batch_scan_and_alert.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── filter-engine/
│   ├── app.py
│   ├── Dockerfile
│   └── requirements.txt
│
└── docker-compose.yml
```

---

## Telegram Scraper

- Monitors configured Telegram channels in real time
- Downloads attached files into `/files`
- Forwards file paths to the extractor engine
- Gracefully skips expired or invalid invite links

### Requirements

Create Telegram API credentials:

https://my.telegram.org/auth

`.env` variables:

```
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
TELEGRAM_PHONE=
TARGET_CHANNELS=
```

---

## Extractor Engine

Parses file contents and extracts:

- Email addresses
- Credentials (`email:password` patterns)

Supported formats:

- TXT, CSV, LOG
- PDF
- ZIP, RAR, 7z

Example output:

```json
{
  "emails": ["user@example.edu"],
  "creds": [
    {
      "email": "user@example.edu",
      "password": "ExposedPassword123"
    }
  ]
}
```

To prevent alert fatigue:
- Processed files are moved to `/files/_processed`
- Alerted credentials are tracked in `/files/.alerted_creds.json`

---

## Filter Engine

Receives extractor output and forwards **only in-scope exposure**, based on:

- `SCOPE_DOMAIN` (e.g. `example.edu`)
- Optional `SCOPE_EMAIL` (substring match for a specific account)

Both emails and credentials are filtered before being sent to n8n.

---

## n8n → Slack

The n8n workflow:

- Validates extracted credentials
- Classifies results:
  - ✅ Valid credentials
  - ❌ Invalid but exposed credentials
- Aggregates findings **per file**
- Sends a **single Slack alert per file**

Example alert:

```
🚨 CONFIRMED CREDENTIAL COMPROMISE

Source file:
n8n_test_retest_v2.txt

Valid credentials detected:
• user1@example.edu
• user2@example.edu

Also exposed (invalid credentials):
• user3@example.edu

Immediate actions required:
- Force password reset immediately
- Review recent login activity
- Invalidate active sessions
```

---

## Deployment

Start all services:

```bash
docker compose up -d
```

Containers:
- telegram-scraper
- extractor-engine
- filter-engine

---

## Testing (Extractor-Only)

For controlled testing without Telegram:

```bash
rm -f /files/.alerted_creds.json
rm -f /files/_processed/n8n_test*
```

```bash
cat > /files/n8n_test.txt << 'EOF'
alpha@example.edu:BadPass123
beta@example.edu:WrongPass456
admin@example.edu:CorrectPass789
EOF
```

```bash
python /app/scripts/batch_scan_and_alert.py
```

---

## Troubleshooting

### Telegram session locked

```bash
rm -f /session_storage/scraper.session*
# restart container
```

### “All matches already alerted”
Deduplication is working as designed. Reset state only for testing.

### Slack formatting issues
Build message content in an n8n Code node before passing to Slack (simple text is the most reliable).

---

## Security Notes

- Telegram session files must remain private
- Slack credentials must be protected
- Files remain local and are not uploaded externally
- Designed to minimise false positives and alert noise

---

## Future Enhancements

- TheHive case creation
- OpenCTI enrichment
- Severity scoring
- Weekly exposure summaries

---

## Author

Mary Amoah  
Developed for academic SOC monitoring and threat intelligence operations.
