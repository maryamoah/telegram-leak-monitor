import os
import re
import zipfile
import py7zr
import rarfile
from PyPDF2 import PdfReader

# =========================================================
# REGEX DEFINITIONS (bytes-safe)
# =========================================================

# Standard email
EMAIL_RE = re.compile(
    rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    re.IGNORECASE
)

# email:password
CRED_RE = re.compile(
    rb"(?P<user>[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})"
    rb"(?P<sep>[:|,;])"
    rb"(?P<pw>[^\s]{1,100})",
    re.IGNORECASE
)

# url:email:password   (Telegram combo-style leaks)
URL_CRED_RE = re.compile(
    rb"https?://[^\s:]+:"
    rb"(?P<user>[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})"
    rb":"
    rb"(?P<pw>[^\s]{1,200})",
    re.IGNORECASE
)

# =========================================================
# FILE READERS (binary-safe)
# =========================================================

def read_raw(path: str, limit: int = 10_000_000) -> bytes:
    """
    Legacy raw reader (kept for compatibility, NOT used for large text files)
    """
    try:
        with open(path, "rb") as f:
            return f.read(limit)
    except Exception:
        return b""


def read_raw_stream(path: str, chunk_size: int = 4_000_000):
    """
    Stream large text files safely in chunks.
    Prevents missing leaks beyond first N bytes.
    """
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    except Exception:
        return


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

    # -----------------------------------------------------
    # Email extraction
    # -----------------------------------------------------
    for e in EMAIL_RE.findall(raw):
        emails.add(e.decode(errors="ignore").lower())

    # -----------------------------------------------------
    # Credentials: email:password
    # -----------------------------------------------------
    for m in CRED_RE.finditer(raw):
        email = m.group("user").decode(errors="ignore").lower()
        password = m.group("pw").decode(errors="ignore")

        creds.append({
            "email": email,
            "password": password
        })

        emails.add(email)

    # -----------------------------------------------------
    # Credentials: url:email:password (Telegram combo dumps)
    # -----------------------------------------------------
    for m in URL_CRED_RE.finditer(raw):
        email = m.group("user").decode(errors="ignore").lower()
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
# PUBLIC ENTRYPOINT (EXPECTED BY filter-engine/app.py)
# =========================================================

def extract_emails(path: str) -> dict:
    """
    Entry point used by extractor-engine/app.py
    """

    if not path or not os.path.exists(path):
        return {"emails": [], "creds": []}

    lower = path.lower()

    # Binary / archive formats (safe to load fully)
    if lower.endswith(".pdf"):
        return extract_all(read_pdf(path))

    if lower.endswith(".zip"):
        return extract_all(read_zip(path))

    if lower.endswith(".rar"):
        return extract_all(read_rar(path))

    if lower.endswith(".7z"):
        return extract_all(read_7z(path))

    # 🔥 Stream large text files (.txt, .log, .csv, etc.)
    emails = set()
    creds = []

    for chunk in read_raw_stream(path):
        res = extract_all(chunk)
        emails.update(res.get("emails", []))
        creds.extend(res.get("creds", []))

    return {
        "emails": sorted(emails),
        "creds": creds
    }
