from flask import Flask, request, jsonify
import os
import requests
from extractor import extract_all

app = Flask(__name__)

# Where to send extracted data
FILTER_ENDPOINT = "http://filter-engine:7000/ingest"

# Max bytes to read from files (avoid huge dumps)
MAX_READ_BYTES = int(os.getenv("MAX_READ_BYTES", "5000000"))


def read_content_from_path(path: str) -> str:
    """
    Safely read up to MAX_READ_BYTES from a file and return text.
    """
    try:
        with open(path, "rb") as f:
            data = f.read(MAX_READ_BYTES)
        return data.decode(errors="ignore")
    except Exception as e:
        print(f"[extractor] Failed to read {path}: {e}", flush=True)
        return ""


@app.route("/extract", methods=["POST"])
def extract():
    data = request.get_json() or {}

    filepath = data.get("filepath")
    inline_text = data.get("text")

    # Decide source of content: file OR raw text
    content = ""

    # Case 1: file-based extraction (from scraper)
    if filepath:
        if not str(filepath).startswith("/files"):
            return jsonify({"error": "Invalid file path"}), 400

        content = read_content_from_path(filepath)

    # Case 2: direct text (scraper sends raw Telegram message text)
    elif inline_text:
        content = str(inline_text)

    else:
        return jsonify({"error": "No filepath or text provided"}), 400

    # Run our extractor core (emails + password combos)
    extracted = extract_all(content) or {}
    emails = extracted.get("emails") or []
    creds = extracted.get("creds") or []

    result = {
        "filepath": filepath,
        "text_len": len(content),
        "emails": emails,
        "creds": creds,
    }

    # Forward to filter-engine if we found anything useful
    payload = {}

    if emails:
        payload["emails"] = emails

    # creds are optional extra data – filter-engine will safely ignore unknown keys
    if creds:
        payload["creds"] = creds

    if payload:
        try:
            resp = requests.post(FILTER_ENDPOINT, json=payload, timeout=10)
            print(
                f"[extractor] Forwarded {len(emails)} emails, "
                f"{len(creds)} creds -> filter (status {resp.status_code})",
                flush=True,
            )
        except Exception as e:
            print(f"[extractor] Failed to forward to filter-engine: {e}", flush=True)

    return jsonify(result), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001)
