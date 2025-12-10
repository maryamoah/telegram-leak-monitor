from flask import Flask, request, jsonify
import os

from extractor import extract_all

MAX_BYTES = int(os.getenv("MAX_READ_BYTES", "5000000"))

app = Flask(__name__)

# extractor → filter-engine
FILTER_ENDPOINT = "http://filter-engine:7000/ingest"


@app.route("/extract", methods=["POST"])
def extract():
    data = request.get_json(silent=True) or {}

    filepath = data.get("filepath")
    text = data.get("text")

    # --- Case 1: File path provided ---
    if filepath:
        if not filepath.startswith("/files"):
            return jsonify({"error": "Invalid file path"}), 400

        try:
            with open(filepath, "rb") as f:
                raw = f.read(MAX_BYTES)
            content = raw.decode("utf-8", errors="ignore")
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # --- Case 2: Raw text message from scraper ---
    elif text:
        content = text

    else:
        return jsonify({"error": "No text or filepath provided"}), 400

    # Extract emails + credentials
    result = extract_all(content)
    emails = result.get("emails", [])

    # Forward only emails to filter-engine
    if emails:
        import requests
        try:
            resp = requests.post(
                FILTER_ENDPOINT,
                json={"emails": emails},
                timeout=10
            )
            print(f"[extractor] Forwarded {emails} → filter (status {resp.status_code})")
        except Exception as e:
            print("[extractor] Forward failed:", e)

    return jsonify(result), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001)
