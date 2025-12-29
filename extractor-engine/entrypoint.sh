#!/bin/sh
set -e

echo "[+] Starting extractor API (Flask)"
python /app/app.py &

echo "[+] Starting cron scheduler (supercronic)"
exec supercronic /etc/cronjobs
