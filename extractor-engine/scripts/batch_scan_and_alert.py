import glob
import os
import json
import requests
from extractor import extract_emails

FILES_DIR = "/files"
FILTER_URL = "http://filter-engine:7000/ingest"
PROCESSED_DIR = "/files/_processed"
STATE_FILE = "/files/.alerted_creds.json"

os.makedirs(PROCESSED_DIR, exist_ok=True)

if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as f:
        alerted = set(tuple(x) for x in json.load(f))
else:
    alerted = set()

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

    payload = {
        "filepath": os.path.basename(f),
        "emails": sorted({c["email"] for c in fresh_creds}),
        "creds": fresh_creds,
    }

    resp = requests.post(FILTER_URL, json=payload, timeout=30)
    print(f"    [+] Alert sent → status {resp.status_code}")

    os.rename(f, os.path.join(PROCESSED_DIR, os.path.basename(f)))
    print("    [+] File moved to _processed")

with open(STATE_FILE, "w") as f:
    json.dump(list(alerted), f)

print("\n[✓] Batch scan complete")
