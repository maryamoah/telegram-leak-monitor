from flask import Flask, request, jsonify
import os
import requests

from extractor import extract_emails

app = Flask(__name__)

# =========================================================
# ENVIRONMENT
# =========================================================

N8N_WEBHOOK = os.getenv("N8N_WEBHOOK")

# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health", methods=["GET"])
def health():
    return "ok", 200

# =========================================================
# EXTRACTION ENDPOINT
# =========================================================

@app.route("/extract", methods=["POST"])
def extract():
    data = request.get_json(silent=True) or {}
    path = data.get("filepath")

    # ---- Basic path safety ----
    if not path or not isinstance(path, str) or not path.startswith("/files"):
        return jsonify({"error": "Invalid file path"}), 400

    # ---- Run extractor ----
    result = extract_emails(path)

    emails = result.get("emails", [])
    creds = result.get("creds", [])

    if not emails and not creds:
        return jsonify({
            "status": "no scoped data",
            "source": os.path.basename(path)
        }), 200

    payload = {
        "source": os.path.basename(path),
        "emails": emails,
        "email_count": len(emails),
        "creds": creds,
        "cred_count": len(creds),
    }

    # ---- Forward to n8n if configured ----
    if not N8N_WEBHOOK:
        print(
            "[extractor] N8N_WEBHOOK not set, skipping forward",
            flush=True
        )
        return jsonify(payload), 200

    try:
        r = requests.post(
            N8N_WEBHOOK,
            json=payload,
            timeout=15
        )
        print(
            f"[extractor] forwarded "
            f"{len(creds)} creds / {len(emails)} emails "
            f"from {path} (status {r.status_code})",
            flush=True
        )
    except Exception as e:
        print(
            f"[extractor] forward failed for {path}: {e}",
            flush=True
        )

    return jsonify(payload), 200

# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    print("Extractor running on 0.0.0.0:8001", flush=True)
    app.run(host="0.0.0.0", port=8001)
