import os
import re
import zipfile
import py7zr
import rarfile
from PyPDF2 import PdfReader

# =========================================================
# REGEX DEFINITIONS (bytes-safe)
# =========================================================

EMAIL_RE = re.compile(
    rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    re.IGNORECASE
)

CRED_RE = re.compile(
    rb"(?P<user>[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})"
    rb"(?P<sep>[:|,;])"
    rb"(?P<pw>[^\s]{1,50})",
    re.IGNORECASE
)

# =========================================================
# FILE READERS (binary-safe)
# =========================================================

def read_raw(path: str, limit: int = 10_000_000) -> bytes:
    try:
        with open(path, "rb") as f:
            return f.read(limit)
    except Exception:
        return b""


def read_pdf(path: str) -> bytes:
    try:
        reader = PdfReader(path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text.encode(errors="ignore")
    except Exception:
        return b""


def read_zip(path: str) -> bytes:
    buf = b""
    try:
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                try:
                    buf += z.read(name)
                except Exception:
                    pass
    except Exception:
        pass
    return buf


def read_rar(path: str) -> bytes:
    buf = b""
    try:
        with rarfile.RarFile(path) as rf:
            for entry in rf.infolist():
                try:
                    buf += rf.read(entry)
                except Exception:
                    pass
    except Exception:
        pass
    return buf


def read_7z(path: str) -> bytes:
    buf = b""
    try:
        with py7zr.SevenZipFile(path, "r") as z:
            files = z.readall()
            for _, f in files.items():
                try:
                    buf += f.read()
                except Exception:
                    pass
    except Exception:
        pass
    return buf

# =========================================================
# CORE EXTRACTION LOGIC
# =========================================================

def extract_all(raw: bytes) -> dict:
    """
    Extract:
      - emails
      - credential pairs (email + password)
    """

    if not isinstance(raw, (bytes, bytearray)):
        raw = b""

    emails = set()
    creds = []

    # --- Emails ---
    for e in EMAIL_RE.findall(raw):
        emails.add(e.decode(errors="ignore"))

    # --- Credentials ---
    for m in CRED_RE.finditer(raw):
        email = m.group("user").decode(errors="ignore")
        password = m.group("pw").decode(errors="ignore")

        creds.append({
            "email": email,
            "password": password
        })

        emails.add(email)

    return {
        "emails": sorted(emails),
        "creds": creds
    }

# =========================================================
# PUBLIC ENTRYPOINT (EXPECTED BY app.py)
# =========================================================

def extract_emails(path: str) -> dict:
    """
    Entry point used by extractor-engine/app.py
    """

    if not path or not os.path.exists(path):
        return {"emails": [], "creds": []}

    lower = path.lower()

    if lower.endswith(".pdf"):
        raw = read_pdf(path)
    elif lower.endswith(".zip"):
        raw = read_zip(path)
    elif lower.endswith(".rar"):
        raw = read_rar(path)
    elif lower.endswith(".7z"):
        raw = read_7z(path)
    else:
        raw = read_raw(path)

    return extract_all(raw)
