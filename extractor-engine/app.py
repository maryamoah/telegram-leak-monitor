from flask import Flask, request, jsonify
import os
import requests
from extractor import extract_all

app = Flask(__name__)

FILTER_ENDPOINT = "http://filter-engine:7000/ingest"


@app.route("/extract", methods=["POST"])
def extract():
    data = request.get_json() or {}
    path = data.get("filepath")
    text_input = data.get("text")

    # Case 1: Text supplied directly from scraper
    if text_input:
        result = extract_all_from_text(text_input)
        requests.post(FILTER_ENDPOINT, json={"emails": result["emails"]})
        return jsonify(result), 200

    # Case 2: File supplied
    if not path or not path.startswith("/files"):
        return jsonify({"error": "Invalid file path"}), 400

    result = extract_all(path)

    # Forward to filter
    if result["emails"] or result["creds"]:
        try:
            requests.post(FILTER_ENDPOINT, json=result, timeout=10)
        except Exception as e:
            print("[extractor] forwarding failed:", e)

    return jsonify(result), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001)
