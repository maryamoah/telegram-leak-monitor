from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

SCOPE = os.getenv("SCOPE_DOMAIN", "squ.edu.om")
WEBHOOK = os.getenv("N8N_WEBHOOK")

@app.route("/ingest", methods=["POST"])
def ingest():
    data = request.get_json()
    emails = data.get("emails", [])

    matched = [e for e in emails if SCOPE in e]

    if matched:
        try:
            requests.post(WEBHOOK, json={"matches": matched})
        except:
            pass

    return jsonify({"matches": matched}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7000)
