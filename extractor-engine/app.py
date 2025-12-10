from flask import Flask, request, jsonify
import requests
import os
from extractor import extract_all, EMAIL_RE

app = Flask(__name__)

# Where to send extracted emails
FILTER_ENDPOINT = "http://filter-engine:7000/ingest"


@app.route("/extract", methods=["POST"])
def extract():
    data = request.get_json() or {}
    path = data.get("filepath")

    if not path or not path.startswith("/files"):
        return jsonify({"error": "Invalid file path"}), 400

    # Extract text & emails from file
    text = extract_all(path)
    emails = EMAIL_RE.findall(text)

    result = {
        "filepath": path,
        "emails": emails,
    }

    # Forward full email list (for this file) to filter-engine
    if emails:
        try:
            resp = requests.post(FILTER_ENDPOINT, json=result, timeout=10)
            print(f"[extractor] Forwarded {len(emails)} emails from {path} -> filter (status {resp.status_code})")
        except Exception as e:
            print("[extractor] Failed to forward to filter-engine:", e)

    return jsonify(result), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001)
