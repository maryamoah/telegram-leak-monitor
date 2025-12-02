import os
import requests
from flask import Flask, request, jsonify
from logger import log

app = Flask(__name__)

DOMAIN = os.getenv("SCOPE_DOMAIN")
WEBHOOK = os.getenv("N8N_WEBHOOK")

@app.route("/ingest", methods=["POST"])
def ingest():
    filepath = request.json["filepath"]
    
    log(f"Processing file: {filepath}")

    extractor = requests.post(
        "http://extractor-engine:8001/extract",
        json={"filepath": filepath}
    ).json()

    emails = extractor.get("emails", [])
    scoped = [e for e in emails if e.endswith(DOMAIN)]

    if scoped:
        log(f"[!] Leak detected: {scoped}")
        requests.post(WEBHOOK, json={
            "file": filepath,
            "emails": scoped
        })
    else:
        log("No relevant emails found.")

    return jsonify({"status": "ok"})

app.run(host="0.0.0.0", port=7000)
