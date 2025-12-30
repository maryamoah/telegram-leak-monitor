#!/usr/bin/env python3
import sys
import os
import glob
import json
import time
import requests

# Make sure /app is importable (cron-safe)
sys.path.insert(0, "/app")

from extractor import extract_emails

FILES_DIR      = "/files"
PROCESSED_DIR  = "/files/_processed"
FILTER_URL     = os.getenv("FILTER_URL", "http://filter-engine:7000/ingest")
STATE_FILE     = "/files/.alerted_creds.json"

BATCH_SIZE     = int(os.getenv("BATCH_SIZE", "50"))
POST_TIMEOUT   = int(os.getenv("POST_TIMEOUT", "15"))
POST_RETRIES   = int(os.getenv("POST_RETRIES", "3"))
RETRY_SLEEP    = int(os.getenv("RETRY_SLEEP", "5"))

os.makedirs(PROCESSED_DIR, exist_ok=True)

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return set(tuple(x) for x in json.load(f))
        except Exception:
            return set()
    return set()

def save_state(alerted_set):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(list(alerted_set), f)
    os.replace(tmp, STATE_FILE)

def chunks(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]

alerted = load_state()

files = sorted(
    f for f in glob.glob(f"{FILES_DIR}/*.txt")
    if not f.startswith(f"{PROCESSED_DIR}/")
)

for f in files:
    base = os.path.basename(f)

    # Skip underscore files (test files etc.)
    if base.startswith("_"):
        continue

    print(f"\n[+] Scanning {f}", flush=True)

    try:
        result = extract_emails(f)
    except Exception as e:
        print(f"    [!] extract_emails failed: {e}", flush=True)
        continue

    creds = result.get("creds") or []
    if not creds:
        print("    [-] No in-scope matches", flush=True)
        continue

    fresh = []
    for c in creds:
        key = (c.get("email", ""), c.get("password", ""))
        if key[0] and key[1] and key not in alerted:
            alerted.add(key)
            fresh.append(c)

    if not fresh:
        print("    [-] Matches already alerted earlier", flush=True)
        continue

    print(f"    [+] New credentials: {len(fresh)}", flush=True)

    sent_any = False

    for batch in chunks(fresh, BATCH_SIZE):
        payload = {
            "source": base,
            "matches": sorted({c["email"] for c in batch if c.get("email")}),
            "count": len({c["email"] for c in batch if c.get("email")}),
            "creds": batch,
        }

        ok = False
        for attempt in range(1, POST_RETRIES + 1):
            try:
                r = requests.post(FILTER_URL, json=payload, timeout=POST_TIMEOUT)
                if r.status_code == 200:
                    ok = True
                    break
                print(f"    [!] HTTP {r.status_code} attempt {attempt}", flush=True)
            except Exception as e:
                print(f"    [!] POST failed attempt {attempt}: {e}", flush=True)
            time.sleep(RETRY_SLEEP)

        if ok:
            sent_any = True
            print(f"    [+] Batch sent ({len(batch)} creds)", flush=True)
        else:
            print(f"    [!] Batch failed ({len(batch)} creds)", flush=True)

    # Move file only if we successfully sent something
    if sent_any:
        dst = os.path.join(PROCESSED_DIR, base)
        try:
            # File may have been moved already by another run
            if os.path.exists(f):
                os.replace(f, dst)
                print("    [+] File moved to _processed", flush=True)
            else:
                print("    [!] File already missing; not moving", flush=True)
        except Exception as e:
            print(f"    [!] Move failed: {e}", flush=True)
    else:
        print("    [!] Nothing sent; file retained", flush=True)

save_state(alerted)
print("\n[✓] Batch scan complete", flush=True)
