import sys
import os

# ⬇️ MUST be before importing extractor
sys.path.insert(0, "/app")

import glob
import json
import time
import requests
from extractor import extract_emails

# Allow importing extractor from parent dir
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

FILES_DIR = "/files"
PROCESSED_DIR = "/files/_processed"
FILTER_URL = "http://filter-engine:7000/ingest"
STATE_FILE = "/files/.alerted_creds.json"

# Tunables
BATCH_SIZE = 50          # creds per POST
POST_TIMEOUT = 15        # seconds
POST_RETRIES = 3
RETRY_SLEEP = 5          # seconds between retries

os.makedirs(PROCESSED_DIR, exist_ok=True)

# --------------------------------------------------
# Load alerted credential state
# --------------------------------------------------
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as f:
        alerted = set(tuple(x) for x in json.load(f))
else:
    alerted = set()

# --------------------------------------------------
# Utility: chunk a list
# --------------------------------------------------
def chunks(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]

# --------------------------------------------------
# Scan files
# --------------------------------------------------
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

    # Deduplicate against historical alerts
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

    # --------------------------------------------------
    # Send in batches
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
                    timeout=POST_TIMEOUT
                )

                if resp.status_code == 200:
                    sent_any = True
                    print(
                        f"    [+] Batch sent ({len(batch)} creds)"
                    )
                    break
                else:
                    print(
                        f"    [!] HTTP {resp.status_code}, retrying..."
                    )

            except requests.exceptions.RequestException as e:
                print(
                    f"    [!] POST failed (attempt {attempt}): {e}"
                )

            time.sleep(RETRY_SLEEP)

    # --------------------------------------------------
    # Move file only if at least one batch succeeded
    # --------------------------------------------------
    if sent_any:
        os.rename(
            f,
            os.path.join(PROCESSED_DIR, os.path.basename(f))
        )
        print("    [+] File moved to _processed")
    else:
        print("    [!] No batches sent successfully; file retained")

# --------------------------------------------------
# Persist alerted state
# --------------------------------------------------
with open(STATE_FILE, "w") as f:
    json.dump(list(alerted), f)

print("\n[✓] Batch scan complete")
