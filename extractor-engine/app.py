from flask import Flask, request, jsonify
import os
import requests

from extractor import (
    read_raw,
    extract_all,
)

app = Flask(__name__)

FILTER_ENDPOINT = "http://filter-engine:7000/ingest"
SCOPE_DOMAIN = (os.getenv("SCOPE_DOMAIN") or "").lower()

@app.route("/extract", methods=["POST"])
def extract():
    data = request.get_json(silent=True) or {}
    path = data.get("filepath")

    if not path or not path.startswith("/files"):
        return jsonify({"error": "Invalid file path"}), 400

    # 1️⃣ Read raw file safely
    raw = read_raw(path)

    # 2️⃣ Extract emails + creds
    result = extract_all(raw)

    # 3️⃣ FILTER TO DOMAIN (🔥 critical step)
    emails = [
        e for e in result["emails"]
        if SCOPE_DOMAIN and e.lower().endswith("@" + SCOPE_DOMAIN)
    ]

    creds = [
        c for c in result["creds"]
        if c["email"].lower().endswith("@" + SCOPE_DOMAIN)
    ]

    if not emails and not creds:
        # Nothing relevant → do NOT forward
        return jsonify({"status": "no scoped data"}), 200

    payload = {
        "source": path,
        "emails": emails,
        "creds": creds,
    }

    # 4️⃣ Forward only scoped data
    try:
        resp = requests.post(FILTER_ENDPOINT, json=payload, timeout=15)
        print(
            f"[extractor] {len(emails)} emails / {len(creds)} creds "
            f"forwarded from {path} (status {resp.status_code})"
        )
    except Exception as e:
        print("[extractor] Forward failed:", e)

    return jsonify(payload), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001)
