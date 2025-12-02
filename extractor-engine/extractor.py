import os
import re
import json
import csv
import zipfile
from pdfminer.high_level import extract_text

EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@([a-zA-Z0-9.-]+)"

def extract_from_file(path):
    hits = []

    if path.endswith(".zip"):
        with zipfile.ZipFile(path, 'r') as z:
            for f in z.namelist():
                try:
                    content = z.read(f).decode(errors="ignore")
                    hits += re.findall(EMAIL_REGEX, content)
                except:
                    pass

    elif path.endswith(".txt"):
        with open(path, "r", errors="ignore") as f:
            hits += re.findall(EMAIL_REGEX, f.read())

    elif path.endswith(".json"):
        try:
            data = json.load(open(path))
            hits += re.findall(EMAIL_REGEX, str(data))
        except:
            pass

    elif path.endswith(".csv"):
        with open(path, newline='', errors="ignore") as f:
            for row in csv.reader(f):
                hits += re.findall(EMAIL_REGEX, ",".join(row))

    elif path.endswith(".pdf"):
        try:
            text = extract_text(path)
            hits += re.findall(EMAIL_REGEX, text)
        except:
            pass

    else:
        # fallback: scan raw bytes
        try:
            raw = open(path, "rb").read().decode(errors="ignore")
            hits += re.findall(EMAIL_REGEX, raw)
        except:
            pass

    return list(set(hits))
