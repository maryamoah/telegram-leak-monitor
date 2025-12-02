from flask import Flask, request, jsonify
from extractor import extract_from_file

app = Flask(__name__)

@app.route("/extract", methods=["POST"])
def extract():
    path = request.json["filepath"]
    results = extract_from_file(path)
    return jsonify({"emails": results})

app.run(host="0.0.0.0", port=8001)
