from flask import Flask, request, jsonify
import requests
import os
from extractor import extract_emails

app = Flask(__name__)

FILTER_ENDPOINT = "http://filter-engine:7000/ingest"


@app.route("/extract", methods=["POST"])
def extract():
    data = request.get_json(silent=True) or {}
    path = data.get("filepath")

    if not path or not os.path.exists(path):
        return jsonify({"error": "Invalid file path"}), 400

    emails = extract_emails(path)

    payload = {
        "emails": emails,
        "source": path
    }

    # Forward ONLY if emails exist
    if emails:
        try:
            resp = requests.post(FILTER_ENDPOINT, json=payload, timeout=10)
            print(
                f"[extractor] Sent {len(emails)} emails → filter (status {resp.status_code})",
                flush=True
            )
        except Exception as e:
            print("[extractor] Forward error:", e, flush=True)

    return jsonify(payload), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001)
