from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

# Environment
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
    emails = data.get("emails") or []

    # Normalise
    cleaned = []
    for e in emails:
        if not e:
            continue
        cleaned.append(str(e).strip().lower())

    # Match against scope
    matched = []
    for e in cleaned:
        if SCOPE_EMAIL and SCOPE_EMAIL in e:
            matched.append(e)
        elif SCOPE_DOMAIN and e.endswith("@" + SCOPE_DOMAIN):
            matched.append(e)

    # De-duplicate
    unique = sorted(set(matched))

    # Forward to n8n if any
    if unique and WEBHOOK:
        try:
            resp = requests.post(WEBHOOK, json={"matches": unique}, timeout=10)
            print(f"Forwarded to n8n: {unique} (status {resp.status_code})", flush=True)
        except Exception as exc:
            print(f"[ERROR] Failed to send to n8n: {exc}", flush=True)

    return jsonify({"new_leaks": unique}), 200


if __name__ == "__main__":
    print("Starting Flask on 0.0.0.0:7000", flush=True)
    app.run(host="0.0.0.0", port=7000)
