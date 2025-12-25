#!/usr/bin/env python3
import sys
import os
import glob
import json
import time
import requests

# --------------------------------------------------
# Ensure extractor import works under cron / Docker
# --------------------------------------------------
sys.path.insert(0, "/app")

from extractor import extract_emails

# --------------------------------------------------
# Configuration
# --------------------------------------------------
FILES_DIR      = "/files"
PROCESSED_DIR  = "/files/_processed"
FILTER_URL     = "http://filter-engine:7000/ingest"
STATE_FILE     = "/files/.alerted_creds.json"

BATCH_SIZE     = 50     # creds per POST
POST_TIMEOUT   = 15     # seconds
POST_RETRIES   = 3
RETRY_SLEEP    = 5      # seconds

os.makedirs(PROCESSED_DIR, exist_ok=True)

# --------------------------------------------------
# Load alerted credential state (persistent dedup)
# --------------------------------------------------
if os.path.exists(STATE_FILE):
    try:
        with open(STATE_FILE, "r") as f:
            alerted = set(tuple(x) for x in json.load(f))
    except Exception:
        alerted = set()
else:
    alerted = set()

# --------------------------------------------------
# Utility: chunk list
# --------------------------------------------------
def chunks(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]

# --------------------------------------------------
# Select candidate files
# --------------------------------------------------
files = sorted(
    f for f in glob.glob(f"{FILES_DIR}/*.txt")
    if not f.startswith(PROCESSED_DIR + "/")
)

# --------------------------------------------------
# Main scan loop
# --------------------------------------------------
for f in files:
    print(f"\n[+] Scanning {f}", flush=True)

    # File might disappear (race / manual cleanup)
    if not os.path.exists(f):
        print("    [!] File missing, skipping", flush=True)
        continue

    try:
        result = extract_emails(f)
    except Exception as e:
        print(f"    [!] Extractor error: {e}", flush=True)
        continue

    if not result.get("creds"):
        print("    [-] No in-scope matches", flush=True)
        continue

    # --------------------------------------------------
    # Deduplicate against historical alerts
    # --------------------------------------------------
    fresh_creds = []
    for c in result["creds"]:
        key = (c["email"], c["password"])
        if key not in alerted:
            alerted.add(key)
            fresh_creds.append(c)

    if not fresh_creds:
        print("    [-] Matches already alerted earlier", flush=True)
        continue

    print(f"    [+] New credentials: {len(fresh_creds)}", flush=True)

    sent_any = False

    # --------------------------------------------------
    # Send to filter-engine in batches
    # --------------------------------------------------
    for batch in chunks(fresh_creds, BATCH_SIZE):
        payload = {
            "source": os.path.basename(f),
            "matches": sorted({c["email"] for c in batch}),
            "count": len(batch),
            "creds": batch,
        }

        for attempt in range(1, POST_RETRIES + 1):
            try:
                resp = requests.post(
                    FILTER_URL,
                    json=payload,
                    timeout=POST_TIMEOUT,
                )

                if resp.status_code == 200:
                    sent_any = True
                    print(
                        f"    [+] Batch sent ({len(batch)} creds)",
                        flush=True,
                    )
                    break
                else:
                    print(
                        f"    [!] HTTP {resp.status_code} (attempt {attempt})",
                        flush=True,
                    )

            except requests.exceptions.RequestException as e:
                print(
                    f"    [!] POST failed (attempt {attempt}): {e}",
                    flush=True,
                )

            time.sleep(RETRY_SLEEP)

    # --------------------------------------------------
    # Move file ONLY if something was sent
    # --------------------------------------------------
    if sent_any:
        dest = os.path.join(PROCESSED_DIR, os.path.basename(f))
        try:
            if os.path.exists(f):
                os.rename(f, dest)
                print("    [+] File moved to _processed", flush=True)
            else:
                print(
                    "    [!] File already missing, skip move",
                    flush=True,
                )
        except Exception as e:
            print(f"    [!] Failed to move file: {e}", flush=True)
    else:
        print("    [!] Nothing sent, file retained", flush=True)

# --------------------------------------------------
# Persist alerted state
# --------------------------------------------------
try:
    with open(STATE_FILE, "w") as f:
        json.dump(list(alerted), f)
except Exception as e:
    print(f"[!] Failed to write state file: {e}", flush=True)

print("\n[✓] Batch scan complete", flush=True)
