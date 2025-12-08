🚨 SQU Telegram Leak Monitor

Automated Threat Intelligence Pipeline for Detecting Telegram Leaks Related to SQU Domains
Telegram → Scraper → Extractor → Filter → n8n → Slack

📝 Overview

This system continuously monitors selected Telegram channels for leaked files, credentials, emails, or data mentioning @squ.edu.om.

When a leak is detected:

Files are automatically downloaded from monitored Telegram channels

Content is parsed using the extractor engine

SQU-related indicators (emails/domains) are filtered

Alerts are forwarded to n8n

n8n transforms the alert and sends a formatted message to Slack

This creates a fully automated Threat Intelligence pipeline for SOC monitoring, with zero manual effort required.

🏗 Project Architecture
┌──────────────────┐
│  Telegram Scraper │  (Telethon)
└───────┬──────────┘
        │ Downloads files + forwards metadata
        ▼
┌────────────────────┐
│  Extractor Engine   │  (PDF, TXT, ZIP, RAR, 7z, strings)
└───────┬────────────┘
        │ Extracts emails/domains
        ▼
┌────────────────────┐
│   Filter Engine     │  (Match @squ.edu.om)
└───────┬────────────┘
        │ Sends true positives only
        ▼
┌────────────────────┐
│       n8n           │
└───────┬────────────┘
        │ Formats alert
        ▼
┌────────────────────┐
│       Slack         │
└────────────────────┘

📁 Repository Structure
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
├── docker-compose.yml
└── README.md   ← (this file)

⚙️ Requirements

Docker + Docker Compose

Portainer (optional, recommended)

Python 3.11 (inside containers)

Slack App with Bot Token

n8n instance (self-hosted)

Telegram API ID + API Hash

Telegram account (receives leaks from channels)

🚀 How It Works
1️⃣ Telegram Scraper

Monitors Telegram channels in real time

Downloads files (TXT, PDF, DOCX, CSV, ZIP, RAR, 7z, images) to /files

Sends text + file path metadata to extractor

2️⃣ Extractor Engine

Extracts indicators from:

Text files

PDFs

Archive files

Binary files using strings

Image filenames

Extracts:

Emails

Domains

3️⃣ Filter Engine

Only forwards indicators containing @squ.edu.om or SQU domains

Reduces noise

Sends true-positive alerts to n8n

4️⃣ n8n

Receives webhook: { "matches": ["email@squ.edu.om"] }

Code node formats a clean SOC alert

Slack node posts message to SOC channel

5️⃣ Slack Output

Example alert:

🚨 Leak Detected in Telegram Channels

Matched Emails:
• user@squ.edu.om

Timestamp: 04/12/2025, 10:26:27

Source: SOC Team

🧰 How to Deploy
1️⃣ Clone the repository
git clone https://github.com/maryamoah/telegram-leak-monitor
cd telegram-leak-monitor

2️⃣ Set environment variables

Create an .env file:

TELEGRAM_API_ID=xxxxxx
TELEGRAM_API_HASH=xxxxxxxxxxxxxxxxxxxxxxx
TELEGRAM_PHONE=+96899999999
N8N_WEBHOOK=https://your-n8n.com/webhook/ti-intel

3️⃣ Deploy with Docker Compose
docker compose up -d


Containers launched:

telegram-scraper

extractor-engine

filter-engine

🔍 How to Test the Pipeline
Test extractor:

Inside extractor container:

echo "test@squ.edu.om" > /files/test.txt
curl -X POST http://localhost:8001/extract -H "Content-Type: application/json" -d '{"filepath": "/files/test.txt"}'

Test filter:
curl -X POST http://localhost:7000/ingest -H "Content-Type: application/json" -d '{"emails":["test@squ.edu.om"]}'

Test n8n → Slack:
curl -X POST https://your-n8n/webhook/ti-intel -H "Content-Type: application/json" -d '{"matches":["test@squ.edu.om"]}'

🔐 Troubleshooting
❌ Telegram scraper: sqlite3.OperationalError: database is locked

Fix:

rm -f /session_storage/scraper.session*
restart container
re-login to Telegram

❌ Extractor returns nothing

File is binary → strings fallback used

File is large → adjust MAX_READ_BYTES

❌ Slack shows raw text

Slack V2 nodes in n8n do not evaluate expressions
Fix:
Use Code Node → Slack node with expression: {{ $json.text }}

❌ n8n workflow won’t save

Slack V2 corruption — delete Slack node, save workflow, re-add Slack.

📌 Security Notes

Do NOT expose Telegram API credentials publicly

Slack Bot token must be protected (xoxb-...)

Filter ensures only SQU-related data triggers alerts

Files remain local and are NOT forwarded to Slack or external systems

🧩 Future Enhancements

Auto-create TheHive cases

Add domain, phone number, hash extraction

Integrate OpenCTI enrichment

Add scoring model (Critical / High / Medium / Low)

Automatic IOC deduplication storage

Telegram media OCR (extract emails from screenshots)
