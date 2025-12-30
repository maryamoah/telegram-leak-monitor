from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

# =========================================================
# ENVIRONMENT
# =========================================================

WEBHOOK = os.getenv("N8N_WEBHOOK")

print("=== Filter engine starting ===", flush=True)
print(f"N8N_WEBHOOK = {'set' if WEBHOOK else 'not set'}", flush=True)

# =========================================================
# HEALTH
# =========================================================

@app.route("/health", methods=["GET"])
def health():
    return "ok", 200

# =========================================================
# INGEST
# =========================================================

@app.route("/ingest", methods=["POST"])
def ingest():
    data = request.get_json(silent=True) or {}

    source = data.get("source") or data.get("filepath") or "unknown"

    emails = data.get("emails")
    if emails is None:
        emails = data.get("matches") or []

    creds = data.get("creds") or []

    # ----------------------------
    # Basic sanity only
    # ----------------------------

    clean_emails = [
        e for e in emails
        if isinstance(e, str) and "@" in e
    ]

    clean_creds = [
        c for c in creds
        if isinstance(c, dict)
        and c.get("email")
        and c.get("password")
    ]

    if not clean_emails and not clean_creds:
        return jsonify({
            "status": "no data",
            "source": source
        }), 200

    # ----------------------------
    # Build payload (standard)
    # ----------------------------

    payload = {
        "source": source,
        "emails": sorted(set(clean_emails)),
        "email_count": len(set(clean_emails)),
    }

    if clean_creds:
        payload["creds"] = clean_creds
        payload["cred_count"] = len(clean_creds)

        # Ensure emails exist if only creds were sent
        if not payload["emails"]:
            payload["emails"] = sorted(
                {c["email"] for c in clean_creds}
            )
            payload["email_count"] = len(payload["emails"])

    # ----------------------------
    # Forward to n8n
    # ----------------------------

    if WEBHOOK:
        try:
            resp = requests.post(
                WEBHOOK,
                json=payload,
                timeout=15
            )
            print(
                f"[filter] forwarded "
                f"{payload.get('email_count', 0)} email(s) "
                f"+ {payload.get('cred_count', 0)} cred(s) "
                f"from {source} (status {resp.status_code})",
                flush=True
            )
        except Exception as exc:
            print(
                f"[filter] forward failed for {source}: {exc}",
                flush=True
            )
    else:
        print(
            "[filter] N8N_WEBHOOK not set, skipping forward",
            flush=True
        )

    return jsonify(payload), 200

# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":
    print("Starting Flask on 0.0.0.0:7000", flush=True)
    app.run(host="0.0.0.0", port=7000)
