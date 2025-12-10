import os
import re
import zipfile
import subprocess
from pathlib import Path

import py7zr
import rarfile
from PyPDF2 import PdfReader

# -----------------------------------------
# EMAIL REGEX
# -----------------------------------------
EMAIL_RE = re.compile(
    rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    re.IGNORECASE,
)

# -----------------------------------------
# PASSWORD-DUMP REGEX  (Upgrade #3)
# matches: email:password
# -----------------------------------------
CRED_RE = re.compile(
    rb"(?P<email>[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})"
    rb"(?P<sep>[:|,;])"
    rb"(?P<pw>[^\s]{1,80})",
    re.IGNORECASE,
)

# ---------------------------------------------------------
# Helper: Read first chunk of file as text
# ---------------------------------------------------------
def read_head(path: str, max_bytes: int = 5_000_000) -> str:
    try:
        with open(path, "rb") as f:
            return f.read(max_bytes).decode(errors="ignore")
    except Exception:
        return ""


def extract_txt(path: str) -> str:
    return read_head(path)


def extract_pdf(path: str) -> str:
    try:
        reader = PdfReader(path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
        return text
    except Exception:
        return ""


def extract_zip(path: str) -> str:
    text = ""
    try:
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                try:
                    data = z.read(name)
                    text += data.decode(errors="ignore")
                except Exception:
                    pass
        return text
    except Exception:
        return ""


def extract_rar(path: str) -> str:
    text = ""
    try:
        with rarfile.RarFile(path) as rf:
            for info in rf.infolist():
                try:
                    data = rf.read(info)
                    text += data.decode(errors="ignore")
                except Exception:
                    pass
        return text
    except Exception:
        return ""


def extract_7z(path: str) -> str:
    text = ""
    try:
        with py7zr.SevenZipFile(path, "r") as z:
            files = z.readall()
            for name, f in files.items():
                try:
                    text += f.read().decode(errors="ignore")
                except Exception:
                    pass
        return text
    except Exception:
        return ""


# ---------------------------------------------------------
# Pattern extractors
# ---------------------------------------------------------
def extract_emails_from_text(text: str) -> list[str]:
    raw = text.encode(errors="ignore")
    found = EMAIL_RE.findall(raw)
    return list({e.decode(errors="ignore") for e in found})


def extract_creds_from_text(text: str) -> list[dict]:
    raw = text.encode(errors="ignore")
    creds = []

    for m in CRED_RE.finditer(raw):
        email = m.group("email").decode(errors="ignore")
        pw = m.group("pw").decode(errors="ignore")
        creds.append({"email": email, "password": pw})

    return creds


# ---------------------------------------------------------
# Fallback binary scanning
# ---------------------------------------------------------
def scan_binary_for_emails(path: str) -> list[str]:
    results = set()
    with open(path, "rb") as f:
        while chunk := f.read(4 * 1024 * 1024):
            found = EMAIL_RE.findall(chunk)
            for e in found:
                results.add(e)
    return [e.decode(errors="ignore") for e in results]


def scan_binary_for_creds(path: str) -> list[dict]:
    results = []
    seen = set()

    with open(path, "rb") as f:
        while chunk := f.read(4 * 1024 * 1024):
            for m in CRED_RE.finditer(chunk):
                email = m.group("email").decode(errors="ignore")
                pw = m.group("pw").decode(errors="ignore")
                key = (email, pw)
                if key not in seen:
                    seen.add(key)
                    results.append({"email": email, "password": pw})

    return results


# ---------------------------------------------------------
# MAIN ENTRYPOINT: extract_all_from_file
# ---------------------------------------------------------
def extract_all(path: str) -> dict:
    """
    Final unified extractor:
      returns { emails: [...], creds: [...] }
    """
    if not os.path.exists(path):
        return {"emails": [], "creds": []}

    lower = path.lower()

    # 1) TEXT
    if lower.endswith((".txt", ".csv", ".log")):
        text = extract_txt(path)
    # 2) PDF
    elif lower.endswith(".pdf"):
        text = extract_pdf(path)
    # 3) ARCHIVES
    elif lower.endswith(".zip"):
        text = extract_zip(path)
    elif lower.endswith(".rar"):
        text = extract_rar(path)
    elif lower.endswith(".7z"):
        text = extract_7z(path)
    else:
        text = ""  # for binaries we skip straight to fallback

    emails = set(extract_emails_from_text(text))
    creds = extract_creds_from_text(text)

    # Fallback scanning (binary dump extraction)
    emails.update(scan_binary_for_emails(path))
    creds.extend(scan_binary_for_creds(path))

    # Ensure dedup
    unique_emails = sorted(emails)

    return {
        "emails": unique_emails,
        "creds": creds
    }
