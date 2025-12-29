from flask import Flask, request, jsonify
import os
import requests

from extractor import extract_emails

app = Flask(__name__)

# Environment
N8N_WEBHOOK = os.getenv("N8N_WEBHOOK")
SCOPE_DOMAIN = (os.getenv("SCOPE_DOMAIN") or "").lower()

# -------------------------
# Health check
# -------------------------
@app.route("/health", methods=["GET"])
def health():
    return "ok", 200


# -------------------------
# Extract endpoint
# -------------------------
@app.route("/extract", methods=["POST"])
def extract():
    data = request.get_json(silent=True) or {}
    path = data.get("filepath")

    if not path or not path.startswith("/files"):
        return jsonify({"error": "Invalid file path"}), 400

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
        r = requests.post(N8N_WEBHOOK, json=payload, timeout=15)
        print(
            f"[extractor] forwarded {len(creds)} creds from {path} "
            f"(status {r.status_code})",
            flush=True
        )
    except Exception as e:
        print("[extractor] forward failed:", e, flush=True)

    return jsonify(payload), 200


if __name__ == "__main__":
    print("Extractor running on 0.0.0.0:8001", flush=True)
    app.run(host="0.0.0.0", port=8001)
