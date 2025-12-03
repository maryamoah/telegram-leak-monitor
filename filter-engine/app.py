from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

SCOPE = os.getenv("SCOPE_DOMAIN", "squ.edu.om").lower()
WEBHOOK = os.getenv("N8N_WEBHOOK")

@app.route("/ingest", methods=["POST"])
def ingest():
    data = request.get_json() or {}
    print("Incoming data:", data)   # <--- ADD THIS
    emails = data.get("emails", [])

    cleaned = [e.strip().lower() for e in emails]
    matched = [e for e in cleaned if SCOPE in e]

    if matched and WEBHOOK:
        try:
            requests.post(WEBHOOK, json={"matches": matched}, timeout=10)
        except Exception as e:
            print("Failed to send to n8n:", e)

return jsonify({"matches": matched}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7000)
