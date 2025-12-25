import sys
import os
import glob
import json
import time
import requests

# ✅ ensure extractor import works under cron
sys.path.insert(0, "/app")

from extractor import extract_emails

FILES_DIR = "/files"
PROCESSED_DIR = "/files/_processed"
FILTER_URL = "http://filter-engine:7000/ingest"
STATE_FILE = "/files/.alerted_creds.json"

BATCH_SIZE = 50
POST_TIMEOUT = 15
POST_RETRIES = 3
RETRY_SLEEP = 5

os.makedirs(PROCESSED_DIR, exist_ok=True)

# ----------------------------
# Load alerted state
# ----------------------------
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as f:
        alerted = set(tuple(x) for x in json.load(f))
else:
    alerted = set()


def chunks(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


files = sorted(
    f for f in glob.glob(f"{FILES_DIR}/*.txt")
    if not f.startswith(f"{PROCESSED_DIR}/")
)

for f in files:
    print(f"\n[+] Scanning {f}")

    result = extract_emails(f)

    if not result["creds"]:
        print("    [-] No in-scope matches")
        continue

    fresh_creds = []
    for c in result["creds"]:
        key = (c["email"], c["password"])
        if key not in alerted:
            alerted.add(key)
            fresh_creds.append(c)

    if not fresh_creds:
        print("    [-] Matches already alerted earlier")
        continue

    print(f"    [+] New credentials: {len(fresh_creds)}")

    sent_any = False

    for batch in chunks(fresh_creds, BATCH_SIZE):
        payload = {
            "source": os.path.basename(f),
            "matches": sorted({c["email"] for c in batch}),
            "creds": batch,
        }

        for attempt in range(POST_RETRIES):
            try:
                r = requests.post(FILTER_URL, json=payload, timeout=POST_TIMEOUT)
                if r.status_code == 200:
                    sent_any = True
                    print(f"    [+] Batch sent ({len(batch)} creds)")
                    break
            except Exception as e:
                print(f"    [!] POST failed: {e}")
            time.sleep(RETRY_SLEEP)

    if sent_any:
        os.rename(f, os.path.join(PROCESSED_DIR, os.path.basename(f)))
        print("    [+] File moved to _processed")
    else:
        print("    [!] Nothing sent, file retained")

with open(STATE_FILE, "w") as f:
    json.dump(list(alerted), f)

print("\n[✓] Batch scan complete")
