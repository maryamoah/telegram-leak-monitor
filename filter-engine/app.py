from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

# Environment variables (public safe — no hardcoded domains)
SCOPE_DOMAIN = (os.getenv("SCOPE_DOMAIN", "") or "").lower()
SCOPE_EMAIL = (os.getenv("SCOPE_EMAIL", "") or "").lower()
WEBHOOK = os.getenv("N8N_WEBHOOK")

print("=== Filter engine starting ===", flush=True)
print(f"SCOPE_DOMAIN = {SCOPE_DOMAIN!r}", flush=True)
print(f"SCOPE_EMAIL  = {SCOPE_EMAIL!r}", flush=True)
print(f"N8N_WEBHOOK  = {WEBHOOK!r}", flush=True)


@app.route("/health", methods=["GET"])
def health():
    return "ok", 200


@app.route("/ingest", methods=["POST"])
def ingest():
    data = request.get_json(silent=True) or {}

    # Extract file source (optional)
    source = data.get("filepath")
    emails = data.get("emails") or []

    # Normalise emails
    cleaned = [
        str(e).strip().lower()
        for e in emails
        if isinstance(e, str) and e.strip()
    ]

    # Apply domain/email filtering
    matched = []
    for e in cleaned:
        if SCOPE_EMAIL and SCOPE_EMAIL in e:
            matched.append(e)
        elif SCOPE_DOMAIN and e.endswith("@" + SCOPE_DOMAIN):
            matched.append(e)

    unique = sorted(set(matched))

    # Build final JSON payload to n8n
    payload = {"matches": unique}
    if source:
        payload["source"] = source  # optional path for grouping (Option A)

    # Forward grouped results to n8n (Option A)
    if unique and WEBHOOK:
        try:
            resp = requests.post(WEBHOOK, json=payload, timeout=10)
            print(f"Forwarded to n8n: {payload} (status {resp.status_code})", flush=True)
        except Exception as exc:
            print(f"[ERROR] Failed to send to n8n: {exc}", flush=True)

    return jsonify(payload), 200


if __name__ == "__main__":
    print("Starting Flask on 0.0.0.0:7000", flush=True)
    app.run(host="0.0.0.0", port=7000)
