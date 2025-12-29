import os
import glob
import json
import time
import requests

FILES_DIR = "/files"
PROCESSED_DIR = "/files/_processed"
STATE_FILE = "/files/.alerted_creds.json"

EXTRACTOR_URL = "http://127.0.0.1:8001/extract"

POST_TIMEOUT = 30
RETRY_SLEEP = 5

os.makedirs(PROCESSED_DIR, exist_ok=True)

# -------------------------
# Load dedup state
# -------------------------
if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r") as f:
        alerted = set(tuple(x) for x in json.load(f))
else:
    alerted = set()

files = sorted(
    f for f in glob.glob(f"{FILES_DIR}/*.txt")
    if not f.startswith(PROCESSED_DIR)
)

for f in files:
    print(f"\n[+] Scanning {f}")

    try:
        r = requests.post(
            EXTRACTOR_URL,
            json={"filepath": f},
            timeout=POST_TIMEOUT
        )
        data = r.json()
    except Exception as e:
        print("    [!] Extractor call failed:", e)
        continue

    creds = data.get("creds", [])

    if not creds:
        print("    [-] No in-scope matches")
        continue

    fresh = []
    for c in creds:
        key = (c["email"], c["password"])
        if key not in alerted:
            alerted.add(key)
            fresh.append(c)

    if not fresh:
        print("    [-] Matches already alerted earlier")
        continue

    # If extractor succeeded → move file
    os.rename(f, os.path.join(PROCESSED_DIR, os.path.basename(f)))
    print(f"    [+] {len(fresh)} new creds → file moved")

# -------------------------
# Save dedup state
# -------------------------
with open(STATE_FILE, "w") as f:
    json.dump(list(alerted), f)

print("\n[✓] Batch scan complete")
