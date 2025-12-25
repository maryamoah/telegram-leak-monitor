from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

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

    # ✅ Support both old + new sender schemas
    source = data.get("filepath") or data.get("source") or "unknown"

    # Sender might call it emails OR matches
    emails_in = data.get("emails")
    if emails_in is None:
        emails_in = data.get("matches") or []
    creds_in = data.get("creds") or []

    # --- normalize emails ---
    cleaned_emails = [
        str(e).strip().lower()
        for e in emails_in
        if isinstance(e, str) and e.strip()
    ]

    # --- email-level filtering ---
    matched_emails = []
    for e in cleaned_emails:
        if SCOPE_EMAIL and SCOPE_EMAIL in e:
            matched_emails.append(e)
        elif SCOPE_DOMAIN and e.endswith("@" + SCOPE_DOMAIN):
            matched_emails.append(e)

    matched_emails = sorted(set(matched_emails))

    # --- credential-level filtering (CRITICAL) ---
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

    # --- build payload ---
    payload = {
        "source": source,
        "matches": matched_emails,
        "count": len(matched_emails),
    }

    if matched_creds:
        payload["creds"] = matched_creds
        # optional: reflect cred count too
        payload["cred_count"] = len(matched_creds)

        # ensure matches includes any emails from creds (so Slack looks right)
        if not matched_emails:
            payload["matches"] = sorted({str(c.get("email","")).lower() for c in matched_creds if c.get("email")})
            payload["count"] = len(payload["matches"])

    # ✅ Forward if ANYTHING matched (emails OR creds)
    should_forward = (len(payload.get("matches", [])) > 0) or (len(payload.get("creds", [])) > 0)

    if should_forward and WEBHOOK:
        try:
            resp = requests.post(WEBHOOK, json=payload, timeout=15)
            print(
                f"[INFO] Forwarded {len(payload.get('matches', []))} match(es) "
                f"+ {len(payload.get('creds', []))} cred(s) from {source} "
                f"(status {resp.status_code})",
                flush=True,
            )
        except Exception as exc:
            print(f"[ERROR] Failed to send to n8n: {exc}", flush=True)

    return jsonify(payload), 200

if __name__ == "__main__":
    print("Starting Flask on 0.0.0.0:7000", flush=True)
    app.run(host="0.0.0.0", port=7000)
