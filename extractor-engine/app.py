from flask import Flask, request, jsonify
import requests
from extractor import extract_all, EMAIL_RE

app = Flask(__name__)

FILTER_ENDPOINT = "http://filter-engine:7000/ingest"

@app.route("/extract", methods=["POST"])
def extract():
    data = request.get_json()
    path = data.get("filepath")

    if not path or not path.startswith("/files"):
        return jsonify({"error": "Invalid file path"}), 400

    text = extract_all(path)
    emails = EMAIL_RE.findall(text)

    result = {"emails": emails}

    # Send to filter engine
    try:
        requests.post(FILTER_ENDPOINT, json=result)
    except:
        pass

    return jsonify(result), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001)
