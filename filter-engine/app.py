from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# Environment variables
SCOPE = os.getenv("SCOPE_DOMAIN", "squ.edu.om").lower()
WEBHOOK = os.getenv("N8N_WEBHOOK")  # Must be set in compose

@app.route("/ingest", methods=["POST"])
def ingest():
    data = request.get_json() or {}
    emails = data.get("emails", [])

    # Match only emails belonging to SQU domain
    matched = [e for e in emails if SCOPE in e.lower()]

    # Forward to n8n only if there are matches AND webhook is set
    if matched and WEBHOOK:
        try:
            requests.post(WEBHOOK, json={"matches": matched}, timeout=10)
        except Exception as e:
            print("Failed to send to n8n:", e)

    return jsonify({"matches": matched}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7000)
