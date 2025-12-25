from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

# Environment
SCOPE_DOMAIN = (os.getenv("SCOPE_DOMAIN", "") or "").lower()
SCOPE_EMAIL  = (os.getenv("SCOPE_EMAIL", "") or "").lower()
WEBHOOK      = os.getenv("N8N_WEBHOOK")

print("=== Filter engine starting ===", flush=True)
print(f"SCOPE_DOMAIN = {SCOPE_DOMAIN!r}", flush=True)
print(f"SCOPE_EMAIL  = {SCOPE_EMAIL!r}", flush=True)
print(f"N8N_WEBHOOK  = {'set' if WEBHOOK else 'not set'}", flush=True)


@app.route("/health", methods=["GET"])
def health():
    return "ok", 200


@app.route("/ingest", methods=["POST"])
def ingest():
    data = request.get_json(silent=True) or {}

    # 🔧 accept BOTH old & new sender formats
    source = data.get("filepath") or data.get("source") or "unknown"

    emails_in = data.get("emails")
    if emails_in is None:
        emails_in = data.get("matches") or []

    creds_in = data.get("creds") or []

    # ----------------------------
    # Normalize emails
    # ----------------------------
    cleaned_emails = [
        str(e).strip().lower()
        for e in emails_in
        if isinstance(e, str) and e.strip()
    ]

    # ----------------------------
    # Email-level filtering
    # ----------------------------
    matched_emails = []
    for e in cleaned_emails:
        if SCOPE_EMAIL and SCOPE_EMAIL in e:
            matched_emails.append(e)
        elif SCOPE_DOMAIN and e.endswith("@" + SCOPE_DOMAIN):
            matched_emails.append(e)

    matched_emails = sorted(set(matched_emails))

    # ----------------------------
    # Credential-level filtering
    # ----------------------------
    matched_creds = []
    for c in creds_in:
        if not isinstance(c, dict):
            continue
        email = str(c.get("email", "")).lower().strip()
        if not email:
            continue

        if SCOPE_EMAIL and SCOPE_EMAIL in email:
            matched_creds.append(c)
        elif SCOPE_DOMAIN and email.endswith("@" + SCOPE_DOMAIN):
            matched_creds.append(c)

    # ----------------------------
    # Build payload for n8n
    # ----------------------------
    payload = {
        "source": source,
        "matches": matched_emails,
        "count": len(matched_emails),
    }

    if matched_creds:
        payload["creds"] = matched_creds
        payload["cred_count"] = len(matched_creds)

        # Ensure matches exist if only creds were sent
        if not matched_emails:
            payload["matches"] = sorted(
                {c["email"].lower() for c in matched_creds if c.get("email")}
            )
            payload["count"] = len(payload["matches"])

    # ----------------------------
    # Forward to n8n if ANY match
    # ----------------------------
    should_forward = (
        len(payload.get("matches", [])) > 0 or
        len(payload.get("creds", [])) > 0
    )

    if should_forward and WEBHOOK:
        try:
            resp = requests.post(WEBHOOK, json=payload, timeout=15)
            print(
                f"[INFO] Forwarded {payload.get('count', 0)} email(s) "
                f"+ {payload.get('cred_count', 0)} cred(s) "
                f"from {source} (status {resp.status_code})",
                flush=True,
            )
        except Exception as exc:
            print(f"[ERROR] Failed to send to n8n: {exc}", flush=True)

    return jsonify(payload), 200


if __name__ == "__main__":
    print("Starting Flask on 0.0.0.0:7000", flush=True)
    app.run(host="0.0.0.0", port=7000)
