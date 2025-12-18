from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

# Environment variables (public-safe)
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

    source = data.get("filepath")
    emails = data.get("emails") or []
    creds  = data.get("creds") or []

    # --- normalize emails ---
    cleaned_emails = [
        str(e).strip().lower()
        for e in emails
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
    for c in creds:
        email = str(c.get("email", "")).lower().strip()
        if not email:
            continue

        if SCOPE_EMAIL and SCOPE_EMAIL in email:
            matched_creds.append(c)
        elif SCOPE_DOMAIN and email.endswith("@" + SCOPE_DOMAIN):
            matched_creds.append(c)

    # --- build payload (SAFE) ---
    payload = {
        "matches": matched_emails,
        "count": len(matched_emails),
    }

    if source:
        payload["source"] = source

    if matched_creds:
        # ⚠️ forward only matched creds, never all
        payload["creds"] = matched_creds

    # --- forward only if something matched ---
    if matched_emails and WEBHOOK:
        try:
            resp = requests.post(WEBHOOK, json=payload, timeout=10)
            print(
                f"[INFO] Forwarded {len(matched_emails)} match(es) "
                f"from {source} (status {resp.status_code})",
                flush=True,
            )
        except Exception as exc:
            print(f"[ERROR] Failed to send to n8n: {exc}", flush=True)

    return jsonify(payload), 200


if __name__ == "__main__":
    print("Starting Flask on 0.0.0.0:7000", flush=True)
    app.run(host="0.0.0.0", port=7000)
