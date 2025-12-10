from flask import Flask, request, jsonify
import os
import requests

from extractor import extract_all   # <— this now EXISTS

app = Flask(__name__)

FILTER_ENDPOINT = "http://filter-engine:7000/ingest"


@app.route("/extract", methods=["POST"])
def extract():
    data = request.get_json() or {}

    filepath = data.get("filepath")
    text_input = data.get("text")

    if not filepath and not text_input:
        return jsonify({"error": "Need 'filepath' or 'text'"}), 400

    # ========= CASE 1: Extract from FILE =========
    if filepath:
        if not filepath.startswith("/files"):
            return jsonify({"error": "Invalid file path"}), 400
        try:
            with open(filepath, "rb") as f:
                raw = f.read()
        except Exception:
            return jsonify({"error": "Failed to read file"}), 400

        result = extract_all(raw)

    # ========= CASE 2: Extract from TEXT =========
    elif text_input:
        raw = text_input.encode(errors="ignore")
        result = extract_all(raw)

    # ---------- Forward to filter-engine ----------
    if result.get("emails"):
        try:
            resp = requests.post(FILTER_ENDPOINT, json=result, timeout=10)
            print(f"[EXTRACTOR] Sent {len(result['emails'])} emails → filter-engine "
                  f"(status {resp.status_code})")
        except Exception as e:
            print(f"[EXTRACTOR ERROR] Failed forwarding: {e}")

    return jsonify(result), 200


if __name__ == "__main__":
    print("Extractor engine running on :8001")
    app.run(host="0.0.0.0", port=8001)
