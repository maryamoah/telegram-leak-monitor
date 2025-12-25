from flask import Flask, request, jsonify
import os
import requests

from extractor import extract_emails

app = Flask(__name__)

# Forward DIRECTLY to n8n for now
N8N_WEBHOOK = os.getenv("N8N_WEBHOOK")
SCOPE_DOMAIN = (os.getenv("SCOPE_DOMAIN") or "").lower()

@app.route("/extract", methods=["POST"])
def extract():
    data = request.get_json(silent=True) or {}
    path = data.get("filepath")

    if not path or not path.startswith("/files"):
        return jsonify({"error": "Invalid file path"}), 400

    # ✅ Correct extractor
    result = extract_emails(path)

    emails = result.get("emails", [])
    creds = result.get("creds", [])

    if not emails and not creds:
        return jsonify({"status": "no scoped data"}), 200

    payload = {
        "source": os.path.basename(path),
        "matches": emails,
        "count": len(emails),
        "creds": creds,
    }

    try:
        resp = requests.post(N8N_WEBHOOK, json=payload, timeout=15)
        print(
            f"[extractor] forwarded {len(creds)} creds from {path} "
            f"(status {resp.status_code})"
        )
    except Exception as e:
        print("[extractor] Forward failed:", e)

    return jsonify(payload), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001)
