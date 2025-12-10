from flask import Flask, request, jsonify
import os
from extractor import extract_emails

app = Flask(__name__)

FILTER_ENDPOINT = "http://filter-engine:7000/ingest"


@app.route("/extract", methods=["POST"])
def extract():
    data = request.get_json() or {}
    path = data.get("filepath")

    if not path or not os.path.exists(path):
        return jsonify({"error": "Invalid file path"}), 400

    # NEW: call upgraded extractor
    emails = extract_emails(path)

    result = {
        "filepath": path,
        "emails": emails,
    }

    # Forward full email list to filter-engine
    try:
        import requests
        resp = requests.post(FILTER_ENDPOINT, json=result, timeout=10)
        print(f"[extractor] forwarded {len(emails)} emails from {path} → filter (status {resp.status_code})")
    except Exception as e:
        print("[extractor] ERROR forwarding to filter:", e)

    return jsonify(result), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001)
