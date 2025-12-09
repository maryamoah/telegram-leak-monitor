from flask import Flask, request, jsonify
import requests, os

app = Flask(__name__)

# -----------------------------
# CONFIGURATION
# -----------------------------
SCOPE = os.getenv("SCOPE_DOMAIN", "example.edu").lower()
WEBHOOK = os.getenv("N8N_WEBHOOK")

# Domains we should never alert on (spam/temporary emails)
BLACKLIST = [
    "tempmail", "mailinator", "dufeed", "10min",
    "sharklasers", "guerrillamail", "dispostable"
]

# Persistent store to avoid duplicate alerts
SEEN_FILE = "/store/seen_emails.txt"
os.makedirs("/store", exist_ok=True)


# -----------------------------
# SEEN EMAIL CACHE HELPERS
# -----------------------------
def load_seen():
    """Load previously alerted emails."""
    if not os.path.exists(SEEN_FILE):
        return set()
    return set(open(SEEN_FILE).read().splitlines())


def save_seen(seen):
    """Persist email list to disk."""
    with open(SEEN_FILE, "w") as f:
        f.write("\n".join(seen))


# -----------------------------
# MAIN INGEST ENDPOINT
# -----------------------------
@app.route("/ingest", methods=["POST"])
def ingest():
    data = request.get_json() or {}
    emails = data.get("emails", [])

    # Normalize + clean punctuation
    cleaned = [
        e.strip().lower().rstrip(".,;!? ")
        for e in emails
        if isinstance(e, str)
    ]

    # Keep only emails under our monitored domain
    scoped = [e for e in cleaned if SCOPE in e]

    # Remove temporary / burner emails
    scoped = [
        e for e in scoped
        if not any(bad in e for bad in BLACKLIST)
    ]

    # Load previously seen emails
    seen = load_seen()

    # Only process new leaks
    new_leaks = [e for e in scoped if e not in seen]

    # If new leaks found → send to n8n + store
    if new_leaks:
        seen.update(new_leaks)
        save_seen(seen)

        if WEBHOOK:
            try:
                requests.post(WEBHOOK, json={"matches": new_leaks}, timeout=10)
                print("Forwarded to n8n:", new_leaks)
            except Exception as e:
                print("Failed to send webhook:", e)

    return jsonify({"new_leaks": new_leaks}), 200


# -----------------------------
# SERVER
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7000)
    
