import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Load environment variables
SCOPE_DOMAIN = os.getenv("SCOPE_DOMAIN", "").lower().strip()
SCOPE_EMAIL = os.getenv("SCOPE_EMAIL", "").lower().strip()
WEBHOOK = os.getenv("N8N_WEBHOOK", "").strip()

def email_matches_scope(email: str) -> bool:
    email = email.lower()

    # Highest priority: explicit email suffix, e.g. "@squ.edu.om"
    if SCOPE_EMAIL and email.endswith(SCOPE_EMAIL):
        return True

    # Domain match: e.g. "squ.edu.om" should match "user@squ.edu.om"
    if SCOPE_DOMAIN and SCOPE_DOMAIN in email:
        return True

    return False


@app.route("/ingest", methods=["POST"])
def ingest():
    data = request.get_json()

    emails = data.get("emails", [])
    if not isinstance(emails, list):
        emails = [emails]

    print("\nIncoming emails:", emails)

    matched = [email for email in emails if email_matches_scope(email)]

    print("Matched:", matched)

    if matched and WEBHOOK:
        print("Forwarded to n8n:", matched)
        try:
            requests.post(WEBHOOK, json={"matches": matched})
        except Exception as e:
            print("Webhook error:", e)

    return jsonify({"new_leaks": matched})
