# Telegram Leak Monitor

Telegram Leak Monitor is an automated pipeline for detecting leaked **credentials** shared in Telegram channels, validating them, and alerting security teams in a controlled, SOC-friendly way.

The system is designed to monitor large Telegram leak dumps, extract credentials related to a specific domain (e.g. `@squ.edu.om`), validate them, and send **aggregated alerts** to Slack via n8n.

---

## How It Works

1. **Telegram Scraper**
   - Listens to configured Telegram channels
   - Downloads shared files into a shared `/files` directory
   - Forwards file paths to the extractor engine

2. **Extractor Engine**
   - Streams and scans large files safely (TXT, archives, PDFs)
   - Extracts:
     - Emails
     - Credentials (`email:password`)
   - Supports very large Telegram dump files
   - Deduplicates credentials to avoid repeat alerts

3. **Filter Engine**
   - Applies scope filtering:
     - Domain-based (`SCOPE_DOMAIN`)
     - Optional email-level filtering
   - Forwards only in-scope emails and credentials to n8n

4. **n8n Workflow**
   - Validates extracted credentials (e.g. SSH / auth checks)
   - Classifies results:
     - ✅ Valid credentials
     - ❌ Invalid but exposed credentials
   - Aggregates results **per file**
   - Sends **one Slack alert per file**

---

## Architecture

```
Telegram
  ↓
telegram-scraper
  ↓
extractor-engine
  ↓
filter-engine
  ↓
n8n
  ↓
Slack
```

---

## Repository Structure

```
telegram-leak-monitor/
├── telegram-scraper/
│   └── app.py
│
├── extractor-engine/
│   ├── extractor.py
│   ├── app.py
│   └── scripts/
│       └── batch_scan_and_alert.py
│
├── filter-engine/
│   └── app.py
│
├── docker-compose.yml
└── README.md
```

---

## Extractor Output Format

```json
{
  "emails": [
    "user@squ.edu.om"
  ],
  "creds": [
    {
      "email": "user@squ.edu.om",
      "password": "ExposedPassword123"
    }
  ]
}
```

---

## Deduplication Behavior

- Processed files are moved to `/files/_processed`
- Alerted credentials are stored in `/files/.alerted_creds.json`

---

## Example Slack Alert

```
🚨 CONFIRMED CREDENTIAL COMPROMISE

Source file:
n8n_test_retest_v2.txt

Valid credentials detected:
- m.amoah@squ.edu.om
- secops@squ.edu.om

Also exposed (invalid credentials):
- alpha@squ.edu.om
```

---

## Deployment

```bash
docker compose up -d
```

---

## Testing Without Telegram

```bash
rm -f /files/.alerted_creds.json
rm -f /files/_processed/n8n_test*
```

```bash
cat > /files/n8n_test.txt << 'EOF'
alpha@squ.edu.om:BadPass123
beta@squ.edu.om:WrongPass456
secops@squ.edu.om:CorrectPass789
EOF
```

```bash
python /app/scripts/batch_scan_and_alert.py
```

---

## Author

Mary Amoah
