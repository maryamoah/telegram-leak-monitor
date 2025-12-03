from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

SCOPE = os.getenv("SCOPE_DOMAIN", "squ.edu.om").lower()
WEBHOOK = os.getenv("N8N_WEBHOOK")

@app.route("/ingest", methods=["POST"])
def ingest():
    data = request.get_json() or {}
    print("Incoming data:", data)   # debug line

    emails = data.get("emails", [])

    # Clean & normalize emails
    cleaned = [e.strip().lower() for e in emails]

    # Match SQU emails
    matched = [e for e in cleaned if SCOPE in e]

    # Send to n8n if matches exist
    if matched and WEBHOOK:
        try:
            requests.post(WEBHOOK, json={"matches": matched}, timeout=10)
            print("Forwarded to n8n:", matched)
        except Exception as e:
            print("Failed to send to n8n:", e)

    return jsonify({"matches": matched}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7000)
    
