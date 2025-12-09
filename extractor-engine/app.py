from flask import Flask, request, jsonify
import requests
from extractor import extract_emails

app = Flask(__name__)

FILTER_ENDPOINT = "http://filter-engine:7000/ingest"


@app.route("/extract", methods=["POST"])
def extract():
    data = request.get_json() or {}
    path = data.get("filepath")

    if not path or not str(path).startswith("/files"):
        return jsonify({"error": "Invalid file path"}), 400

    emails = extract_emails(path)
    result = {"emails": emails}

    # Send to filter-engine (best-effort)
    try:
        requests.post(FILTER_ENDPOINT, json=result, timeout=10)
    except Exception:
        pass

    return jsonify(result), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001)
