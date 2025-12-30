#!/usr/bin/env python3
import sys
import os
import glob
import json
import time
import requests
from typing import Set, Tuple, List

# Make sure /app is importable (cron-safe)
sys.path.insert(0, "/app")

from extractor import extract_emails

# =========================================================
# CONFIG
# =========================================================

FILES_DIR     = "/files"
PROCESSED_DIR = "/files/_processed"
STATE_FILE    = "/files/.alerted_creds.json"

FILTER_URL    = os.getenv("FILTER_URL", "http://filter-engine:7000/ingest")

BATCH_SIZE    = int(os.getenv("BATCH_SIZE", "50"))
POST_TIMEOUT  = int(os.getenv("POST_TIMEOUT", "15"))
POST_RETRIES  = int(os.getenv("POST_RETRIES", "3"))
RETRY_SLEEP   = int(os.getenv("RETRY_SLEEP", "5"))

os.makedirs(PROCESSED_DIR, exist_ok=True)

# =========================================================
# STATE HANDLING
# =========================================================

def load_state() -> Set[Tuple[str, str]]:
    if not os.path.exists(STATE_FILE):
        return set()
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
            return set(tuple(x) for x in data)
    except Exception:
        return set()

def save_state(alerted: Set[Tuple[str, str]]) -> None:
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(list(alerted), f)
    os.replace(tmp, STATE_FILE)

def chunked(items: List[dict], size: int):
    for i in range(0, len(items), size):
        yield items[i:i + size]

# =========================================================
# MAIN
# =========================================================

alerted = load_state()

files = sorted(
    f for f in glob.glob(f"{FILES_DIR}/*.txt")
    if not f.startswith(PROCESSED_DIR + "/")
)

for path in files:
    base = os.path.basename(path)

    # Skip underscore-prefixed files
    if base.startswith("_"):
        continue

    print(f"\n[+] Scanning {path}", flush=True)

    try:
        result = extract_emails(path)
    except Exception as e:
        print(f"    [!] extract_emails failed: {e}", flush=True)
        continue

    creds = result.get("creds") or []
    if not creds:
        print("    [-] No in-scope credentials", flush=True)
        continue

    # -----------------------------------------------------
    # Deduplicate against alert history
    # -----------------------------------------------------

    fresh = []
    for c in creds:
        email = c.get("email")
        password = c.get("password")
        if not email or not password:
            continue

        key = (email, password)
        if key in alerted:
            continue

        alerted.add(key)
        fresh.append(c)

    if not fresh:
        print("    [-] All matches already alerted", flush=True)
        continue

    print(f"    [+] New credentials: {len(fresh)}", flush=True)

    sent_any = False

    # -----------------------------------------------------
    # Send in batches
    # -----------------------------------------------------

    for batch in chunked(fresh, BATCH_SIZE):
        emails = sorted({c["email"] for c in batch if c.get("email")})

        payload = {
            "source": base,
            "emails": emails,
            "email_count": len(emails),
            "creds": batch,
            "cred_count": len(batch),
        }

        ok = False
        for attempt in range(1, POST_RETRIES + 1):
            try:
                r = requests.post(
                    FILTER_URL,
                    json=payload,
                    timeout=POST_TIMEOUT
                )
                if r.status_code == 200:
                    ok = True
                    break
                print(
                    f"    [!] HTTP {r.status_code} (attempt {attempt})",
                    flush=True
                )
            except Exception as e:
                print(
                    f"    [!] POST failed (attempt {attempt}): {e}",
                    flush=True
                )
            time.sleep(RETRY_SLEEP)

        if ok:
            sent_any = True
            print(f"    [+] Batch sent ({len(batch)} creds)", flush=True)
        else:
            print(f"    [!] Batch failed ({len(batch)} creds)", flush=True)

    # -----------------------------------------------------
    # Move file only if at least one batch succeeded
    # -----------------------------------------------------

    if sent_any:
        dst = os.path.join(PROCESSED_DIR, base)
        try:
            if os.path.exists(path):
                os.replace(path, dst)
                print("    [+] File moved to _processed", flush=True)
            else:
                print("    [!] File already moved by another process", flush=True)
        except Exception as e:
            print(f"    [!] Move failed: {e}", flush=True)
    else:
        print("    [!] Nothing sent; file retained", flush=True)

# =========================================================
# FINALIZE
# =========================================================

save_state(alerted)
print("\n[✓] Batch scan complete", flush=True)
