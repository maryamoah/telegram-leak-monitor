import os
import re
import zipfile
import py7zr
import rarfile
from PyPDF2 import PdfReader
from pathlib import Path

# ============================================
# EMAIL extraction (bytes regex)
# ============================================
EMAIL_RE = re.compile(
    rb"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    re.IGNORECASE
)

# ============================================
# PASSWORD dump format:
#   email:password
#   email,password
#   email|password
# ============================================
CRED_RE = re.compile(
    rb"(?P<user>[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})"
    rb"(?P<sep>[:|,;])"
    rb"(?P<pw>[^\s]{1,50})",
    re.IGNORECASE
)


def safe_decode(data: bytes) -> str:
    """Safely decode bytes → string."""
    return data.decode(errors="ignore") if isinstance(data, bytes) else ""


# ========== FILE TYPE READERS ==========

def read_raw(path: str, limit: int = 10_000_000) -> bytes:
    """Read first N bytes of file."""
    try:
        with open(path, "rb") as f:
            return f.read(limit)
    except Exception:
        return b""


def read_pdf(path: str) -> bytes:
    text = ""
    try:
        reader = PdfReader(path)
        for page in reader.pages:
            t = page.extract_text() or ""
            text += t
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
        return buf
    except Exception:
        return b""


def read_rar(path: str) -> bytes:
    buf = b""
    try:
        with rarfile.RarFile(path) as rf:
            for entry in rf.infolist():
                try:
                    buf += rf.read(entry)
                except Exception:
                    pass
        return buf
    except Exception:
        return b""


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
        return buf
    except Exception:
        return b""


# ========== MAIN EXTRACTION ==========

def extract_all(raw: bytes) -> dict:
    """Extract emails + credential pairs from raw bytes."""

    if not isinstance(raw, (bytes, bytearray)):
        raw = b""

    text = raw

    # 1 — Extract emails
    emails = {e.decode(errors="ignore") for e in EMAIL_RE.findall(text)}

    # 2 — Extract credential pairs
    creds = []
    for m in CRED_RE.finditer(text):
        email = m.group("user").decode(errors="ignore")
        pw = m.group("pw").decode(errors="ignore")
        creds.append({"email": email, "password": pw})
        emails.add(email)

    return {
        "emails": sorted(emails),
        "creds": creds
    }
