# Telegram Leak Monitor – Automated Threat Intelligence Pipeline

![Status](https://img.shields.io/badge/status-active-success?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11-blue?style=for-the-badge&logo=python)
![Docker](https://img.shields.io/badge/Docker-Containerized-blue?style=for-the-badge&logo=docker)
![Slack](https://img.shields.io/badge/Slack-Alerts-4A154B?style=for-the-badge&logo=slack)
![n8n](https://img.shields.io/badge/n8n-Automation-orange?style=for-the-badge&logo=n8n)
![Telethon](https://img.shields.io/badge/Telethon-Telegram_API-blue?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

This project monitors Telegram channels for leaked content, downloads files, extracts indicators, filters academic-domain emails (`@example.edu`), and sends alerts to Slack via n8n.

---

## Pipeline

```
Telegram → Scraper → Extractor → Filter → n8n → Slack
```

Use-case: Automatically detect leaked university accounts, credentials, and documents circulating in Telegram communities.

---

## Architecture

```
+---------------------+       +---------------------+       +---------------------+
| Telegram Scraper    | ----> | Extractor Engine    | ----> | Filter Engine       |
| (Telethon)          |       | Extracts emails &   |       | Filters only        |
| Downloads files     |       | domains from files  |       | @example.edu hits   |
+---------------------+       +---------------------+       +---------------------+
                                         |
                                         v
                             +-------------------------+
                             | n8n Automation          |
                             | Formats alert, sends to |
                             | Slack                   |
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

- Monitors Telegram channels in real time  
- Downloads all attached files into `/files`  
- Sends message text + file metadata to the extractor  

### Requirements

Create Telegram API credentials:

https://my.telegram.org/auth

`.env` variables:

```
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
TELEGRAM_PHONE=
```

---

## Extractor Engine

Parses file contents and extracts:

- Email addresses  
- Domains  

Supported formats:

- TXT, CSV, LOG  
- PDF  
- ZIP, RAR, 7z  
- Binary files (via `strings`)

Output JSON example:

```json
{
  "emails": ["test@example.edu"]
}
```

---

## Filter Engine

Receives extractor output and forwards **only matching indicators** containing:

```
@example.edu
```

Example forwarded payload to n8n:

```json
{
  "matches": ["leaked.user@example.edu"]
}
```

---

## n8n → Slack

The n8n workflow receives:

```json
{
  "body": {
    "matches": ["leaked.user@example.edu"]
  }
}
```

A Code node formats the alert message:

```
Leak Detected in Telegram Channels

Matched Emails:
• leaked.user@example.edu

Timestamp: 2025-12-04 10:26
```

Slack delivers the message to your SOC notifications channel.

---

## Deployment

Start all services:

```
docker compose up -d
```

Containers:

- telegram-scraper  
- extractor-engine  
- filter-engine  

---

## Testing

### Test extractor

```
echo "test@example.edu" > /files/test.txt
curl -X POST http://localhost:8001/extract   -H "Content-Type: application/json"   -d '{"filepath":"/files/test.txt"}'
```

### Test filter

```
curl -X POST http://localhost:7000/ingest   -H "Content-Type: application/json"   -d '{"emails":["test@example.edu"]}'
```

### Test n8n webhook

```
curl -X POST https://your-n8n-domain/webhook/ti-intel   -H "Content-Type: application/json"   -d '{"matches":["test@example.edu"]}'
```

---

## Troubleshooting

### Telegram session locked

```
rm -f /session_storage/scraper.session*
restart container
```

### Extractor returns no output
- File may be binary  
- Increase MAX_READ_BYTES  
- ZIP/RAR may be encrypted  

### Slack shows literal `${json}`
Slack V2 cannot evaluate expressions inside text fields.  
Solution: build message in Code node, then pass into Slack node.

### Workflow fails to save
Slack V2 blocks JSON may be corrupted.  
Delete Slack node → save → add new Slack node.

---

## Security Notes

- Telegram session file must remain private  
- Slack Bot token must be secured  
- Files remain local and are never uploaded externally  
- Only domain matches (`@example.edu`) are forwarded  

---

## Future Enhancements

- TheHive case creation  
- OpenCTI enrichment  
- OCR for image-based leaks  
- Alert deduplication DB  
- Severity scoring  

---

## Author

Automated SOC Intelligence Pipeline  
Developed for academic cybersecurity monitoring.
