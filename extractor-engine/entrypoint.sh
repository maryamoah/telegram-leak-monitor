#!/bin/sh
set -e

echo "[+] Starting extractor Flask app..."
python /app/app.py &

echo "[+] Starting cron scheduler..."
exec supercronic /etc/cronjobs
